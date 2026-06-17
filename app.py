import streamlit as st
import datetime
import anthropic
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# フォント登録
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

RESIDENTS = ["末廣皆奈美", "道野生人", "細川隆希"]
ACTIVITY_OPTIONS = [
    "B型就労支援",
    "自由時間（休日）",
    "ホーム内で休養",
    "外出（自由外出）",
    "通院",
    "その他",
]
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def generate_text(name, activity, meal, med, condition):
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    client = anthropic.Anthropic(api_key=api_key)

    context = [f"昼間活動：{activity}", f"体調：{condition}"]
    meal_issues = [t for t, ok in meal.items() if not ok]
    med_issues = [t for t, ok in med.items() if not ok]
    if meal_issues:
        context.append(f"食事未摂取：{'/'.join(meal_issues)}")
    if med_issues:
        context.append(f"服薬未：{'/'.join(med_issues)}")

    prompt = f"""グループホームの日報「本日の様子」欄の文章を書いてください。

入居者名：{name} さん
{chr(10).join(context)}

【文体サンプル（B型就労支援の日）】
本日は起床後、予定通り作業所へ通所いたしました。帰宅後は特に外出されることなく、終日ホーム内にてご自身のペースで穏やかに活動されました。体調を崩される様子も見受けられず、夕食や入浴などの日課を滞りなく済ませ、そのまま就寝いたしました。

【文体サンプル（休日・ホーム内の日）】
本日は作業所がお休みであったため、終日ホーム内にて過ごされました。特に外出されることはなく、室内でご自身のペースに合わせて穏やかに活動を続けられました。体調を崩されることもなく、夕食や入浴などの日課を滞りなく済ませ、予定通り就寝いたしました。

要件：
- 上記サンプルと同じ文体・長さ（3〜4文）で書く
- 活動内容→帰宅後の様子→体調→就寝の流れ
- 食事・服薬に×があれば一言触れる、全て○なら触れない
- 見出し・名前は不要、本文のみ出力
"""
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def build_pdf(date_obj, weekday, day_staff, night_staff, residents_data, special):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=12*mm,
        bottomMargin=12*mm,
    )

    gothic = "HeiseiKakuGo-W5"

    def style(size=10, bold=False, color=colors.black, align="LEFT"):
        return ParagraphStyle(
            "s",
            fontName=gothic,
            fontSize=size,
            textColor=color,
            alignment={"LEFT": 0, "CENTER": 1, "RIGHT": 2}[align],
            leading=size * 1.6,
            wordWrap="CJK",
        )

    story = []

    # ヘッダー
    date_str = f"{date_obj.year}/{date_obj.month}/{date_obj.day}（{weekday}）"
    header_data = [[
        Paragraph("グループホーム　ネクスト　日報", style(14, bold=True, color=colors.white)),
        Paragraph(f"日中：{day_staff}　／　夜間：{night_staff}", style(9, color=colors.white, align="CENTER")),
        Paragraph(date_str, style(10, color=colors.white, align="RIGHT")),
    ]]
    header_table = Table(header_data, colWidths=[90*mm, 65*mm, 25*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3d5a4c")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 10),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 0, 0]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))

    # 入所者カード
    for r in residents_data:
        if r is None:
            empty = Table([[Paragraph("（利用者なし）", style(9, color=colors.gray, align="CENTER"))]],
                          colWidths=[180*mm])
            empty.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]))
            story.append(empty)
            story.append(Spacer(1, 4))
            continue

        def check_cell(ok):
            return Paragraph("○" if ok else "×",
                             style(10, color=colors.HexColor("#4caf50") if ok else colors.HexColor("#cccccc"), align="CENTER"))

        m = r["meal"]
        med = r["med"]

        left_content = [
            [Paragraph(f"{r['name']}　さん", style(12, bold=True))],
            [Paragraph(r["condition"], style(9, color=colors.HexColor("#2e7d32")))],
            [Table([
                [Paragraph("食事", style(8, color=colors.gray)),
                 check_cell(m["朝"]), Paragraph("朝", style(8, color=colors.gray)),
                 check_cell(m["昼"]), Paragraph("昼", style(8, color=colors.gray)),
                 check_cell(m["夕"]), Paragraph("夕", style(8, color=colors.gray))],
                [Paragraph("服薬", style(8, color=colors.gray)),
                 check_cell(med["朝"]), Paragraph("朝", style(8, color=colors.gray)),
                 check_cell(med["昼"]), Paragraph("昼", style(8, color=colors.gray)),
                 check_cell(med["夕"]), Paragraph("夕", style(8, color=colors.gray))],
            ], colWidths=[10*mm, 6*mm, 5*mm, 6*mm, 5*mm, 6*mm, 5*mm])],
            [Spacer(1, 4)],
            [Paragraph(f"昼間活動　{r['activity']}", style(8, color=colors.HexColor("#444444")))],
        ]

        left_table = Table([[row] for row in left_content], colWidths=[55*mm])
        left_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        right_header = Table([[
            Paragraph("本日の様子", style(8, color=colors.gray)),
            Paragraph(f"記：{r['recorder']}", style(8, color=colors.gray, align="RIGHT")),
        ]], colWidths=[55*mm, 65*mm])

        text = r.get("generated_text", "")
        right_content = Table([
            [right_header],
            [Paragraph(text, style(10))],
        ], colWidths=[120*mm])
        right_content.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        card_data = [[left_table, right_content]]
        card = Table(card_data, colWidths=[58*mm, 122*mm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("LINEBEFORE", (1, 0), (1, -1), 0.5, colors.HexColor("#eeeeee")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (0, -1), 10),
            ("LEFTPADDING", (1, 0), (1, -1), 10),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 10),
        ]))
        story.append(card)
        story.append(Spacer(1, 4))

    # 特記事項
    special_data = [
        [Paragraph("ホーム特記事項", style(8, color=colors.gray))],
        [Paragraph(special, style(10))],
    ]
    special_table = Table(special_data, colWidths=[180*mm])
    special_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(special_table)

    doc.build(story)
    buffer.seek(0)
    return buffer


# ── Streamlit UI ──────────────────────────────────────

st.set_page_config(page_title="グループホーム ネクスト 日報", page_icon="📋", layout="centered")
st.title("📋 グループホーム ネクスト　日報作成")

today = datetime.date.today()
weekdays = ["月", "火", "水", "木", "金", "土", "日"]

with st.form("report_form"):
    report_date = st.date_input("日付", value=today)

    st.markdown("---")

    residents_input = []
    for name in RESIDENTS:
        st.subheader(f"👤 {name} さん")
        col1, col2 = st.columns(2)
        with col1:
            condition = st.selectbox("体調", ["良", "要観察", "不調"], key=f"cond_{name}")
            activity_default = 0 if report_date.weekday() < 5 else 1
            activity = st.selectbox("昼間活動", ACTIVITY_OPTIONS, index=activity_default, key=f"act_{name}")
            recorder = st.text_input("記録者", value="寺岡　伊藤・稲田", key=f"rec_{name}")
        with col2:
            st.write("**食事**")
            mc1, mc2, mc3 = st.columns(3)
            meal_m = mc1.checkbox("朝", value=True, key=f"mm_{name}")
            meal_n = mc2.checkbox("昼", value=True, key=f"mn_{name}")
            meal_e = mc3.checkbox("夕", value=True, key=f"me_{name}")
            st.write("**服薬**")
            dc1, dc2, dc3 = st.columns(3)
            med_m = dc1.checkbox("朝 ", value=True, key=f"dm_{name}")
            med_n = dc2.checkbox("昼 ", value=True, key=f"dn_{name}")
            med_e = dc3.checkbox("夕 ", value=True, key=f"de_{name}")

        residents_input.append({
            "name": name,
            "condition": condition,
            "activity": activity,
            "recorder": recorder,
            "meal": {"朝": meal_m, "昼": meal_n, "夕": meal_e},
            "med": {"朝": med_m, "昼": med_n, "夕": med_e},
        })
        st.markdown("---")

    special = st.text_area("ホーム特記事項", value="特になし。", height=80)

    submitted = st.form_submit_button("✨ 日報を生成してPDFダウンロード", use_container_width=True, type="primary")

if submitted:
    weekday = weekdays[report_date.weekday()]
    with st.spinner("Claude が本日の様子を生成中..."):
        for r in residents_input:
            r["generated_text"] = generate_text(
                r["name"], r["activity"], r["meal"], r["med"], r["condition"]
            )
    st.session_state["generated"] = residents_input
    st.session_state["report_date"] = report_date
    st.session_state["special"] = special

if "generated" in st.session_state:
    st.success("生成完了！文章を確認・編集してからPDFをダウンロードしてください。")

    edited_residents = []
    for r in st.session_state["generated"]:
        edited_text = st.text_area(
            f"{r['name']} さん　本日の様子",
            value=r["generated_text"],
            height=120,
            key=f"edit_{r['name']}",
        )
        r_copy = dict(r)
        r_copy["generated_text"] = edited_text
        edited_residents.append(r_copy)

    report_date = st.session_state["report_date"]
    weekday = weekdays[report_date.weekday()]
    special = st.session_state["special"]

    pdf_buf = build_pdf(
        report_date,
        weekday,
        "寺岡",
        "伊藤・稲田",
        edited_residents,
        special,
    )

    filename = f"グループホームネクスト日報 - {report_date.year}年{report_date.month}月{report_date.day}日.pdf"
    st.download_button(
        label="📥 PDFをダウンロード",
        data=pdf_buf,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )
