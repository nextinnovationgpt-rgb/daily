import streamlit as st
import datetime
import anthropic
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# フォント登録
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

ACTIVITY_OPTIONS = [
    "B型就労支援",
    "自由時間（休日）",
    "ホーム内で休養",
    "外出（自由外出）",
    "通院",
    "その他",
]
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# ホーム設定
HOME_CONFIG = {
    "ネクスト": {
        "title": "グループホーム　ネクスト　日報",
        "residents": ["末廣皆奈美", "道野生人", "細川隆希"],
        "empty_slots": [],
        "day_staff": "寺岡",
        "night_staff": "伊藤・稲田",
        "recorder": "寺岡　伊藤・稲田",
        "color": "#3d5a4c",
        "badge_color": "#e8f5e9",
        "badge_border": "#a5d6a7",
        "badge_text": "#2e7d32",
        "check_color": "#4caf50",
        "drive_folder": "ネクスト日報",
        "file_prefix": "グループホームネクスト日報",
        "month_prefix": "N",
    },
    "アモーレ": {
        "title": "グループホーム　アモーレ 3号館　日報",
        "residents": ["館野真央", "小島勇人", "大塚蓮太"],
        "empty_slots": [],
        "day_staff": "丸山",
        "night_staff": "寺岡・坂口",
        "recorder": "寺岡　坂口",
        "color": "#c45e1a",
        "badge_color": "#fff3e0",
        "badge_border": "#ffcc80",
        "badge_text": "#e65100",
        "check_color": "#ff8c00",
        "drive_folder": "アモーレ3号館 日報",
        "file_prefix": "グループホームアモーレ日報",
        "month_prefix": "A",
    },
}

DRIVE_BASE_STR = "/Users/maruyamashunya/Library/CloudStorage/GoogleDrive-nextinnovation.gpt@gmail.com/マイドライブ/グループホームフォルダ"


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


def build_pdf(date_obj, weekday, cfg, residents_data, special):
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
    theme = colors.HexColor(cfg["color"])
    check_col = colors.HexColor(cfg["check_color"])

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
        Paragraph(cfg["title"], style(13, bold=True, color=colors.white)),
        Paragraph(f"日中：{cfg['day_staff']}　／　夜間：{cfg['night_staff']}", style(9, color=colors.white, align="CENTER")),
        Paragraph(date_str, style(10, color=colors.white, align="RIGHT")),
    ]]
    header_table = Table(header_data, colWidths=[85*mm, 60*mm, 35*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), theme),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 10),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))

    # 入所者カード（空スロット込み）
    slot_idx = 0
    resident_idx = 0
    total_slots = len(cfg["residents"]) + len(cfg["empty_slots"])

    for slot in range(total_slots):
        if slot in cfg["empty_slots"]:
            empty = Table([[Paragraph("（利用者なし）", style(9, color=colors.gray, align="CENTER"))]],
                          colWidths=[180*mm])
            empty.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 20),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
            ]))
            story.append(empty)
            story.append(Spacer(1, 4))
            continue

        r = residents_data[resident_idx]
        resident_idx += 1

        def check_cell(ok):
            return Paragraph("○" if ok else "×",
                             style(10, color=check_col if ok else colors.HexColor("#cccccc"), align="CENTER"))

        m = r["meal"]
        med = r["med"]

        left_content = [
            [Paragraph(f"{r['name']}　さん", style(12, bold=True))],
            [Paragraph(r["condition"], style(9, color=colors.HexColor(cfg["badge_text"])))],
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
        ]], colWidths=[50*mm, 60*mm])

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

st.set_page_config(page_title="グループホーム 日報作成", page_icon="📋", layout="centered")

# パスワード認証
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 グループホーム　日報")
    pw = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン", use_container_width=True):
        if pw == "346345":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    st.stop()

# ホーム選択
today = datetime.date.today()

st.markdown("### 🏠 ホームを選択してください")
col1, col2 = st.columns(2)
with col1:
    next_selected = st.session_state.get("home_name", "ネクスト") == "ネクスト"
    if st.button("🟢　ネクスト", use_container_width=True,
                 type="primary" if next_selected else "secondary"):
        st.session_state["home_name_select"] = "ネクスト"
        st.session_state.pop("generated", None)
        st.rerun()
with col2:
    amore_selected = st.session_state.get("home_name", "ネクスト") == "アモーレ"
    if st.button("🟠　アモーレ", use_container_width=True,
                 type="primary" if amore_selected else "secondary"):
        st.session_state["home_name_select"] = "アモーレ"
        st.session_state.pop("generated", None)
        st.rerun()

home_name = st.session_state.get("home_name_select", "ネクスト")
cfg = HOME_CONFIG[home_name]

st.markdown("---")
st.title(f"📋 {cfg['title']}")

with st.form(f"report_form_{home_name}"):
    report_date = st.date_input("日付", value=today)
    st.markdown("---")

    residents_input = []
    for name in cfg["residents"]:
        st.subheader(f"👤 {name} さん")
        col1, col2 = st.columns(2)
        with col1:
            condition = st.selectbox("体調", ["良", "要観察", "不調"], key=f"cond_{home_name}_{name}")
            activity_default = 0 if report_date.weekday() < 5 else 1
            activity = st.selectbox("昼間活動", ACTIVITY_OPTIONS, index=activity_default, key=f"act_{home_name}_{name}")
            recorder = st.text_input("記録者", value=cfg["recorder"], key=f"rec_{home_name}_{name}")
        with col2:
            st.write("**食事**")
            mc1, mc2, mc3 = st.columns(3)
            meal_m = mc1.checkbox("朝", value=True, key=f"mm_{home_name}_{name}")
            meal_n = mc2.checkbox("昼", value=True, key=f"mn_{home_name}_{name}")
            meal_e = mc3.checkbox("夕", value=True, key=f"me_{home_name}_{name}")
            st.write("**服薬**")
            dc1, dc2, dc3 = st.columns(3)
            med_m = dc1.checkbox("朝 ", value=True, key=f"dm_{home_name}_{name}")
            med_n = dc2.checkbox("昼 ", value=True, key=f"dn_{home_name}_{name}")
            med_e = dc3.checkbox("夕 ", value=True, key=f"de_{home_name}_{name}")

        residents_input.append({
            "name": name,
            "condition": condition,
            "activity": activity,
            "recorder": recorder,
            "meal": {"朝": meal_m, "昼": meal_n, "夕": meal_e},
            "med": {"朝": med_m, "昼": med_n, "夕": med_e},
        })
        st.markdown("---")

    special = st.text_area("ホーム特記事項", value="特になし。", height=80, key=f"special_{home_name}")
    submitted = st.form_submit_button("✨ 日報を生成してPDFダウンロード", use_container_width=True, type="primary")

if submitted:
    weekday = WEEKDAYS[report_date.weekday()]
    with st.spinner("Claude が本日の様子を生成中..."):
        for r in residents_input:
            r["generated_text"] = generate_text(
                r["name"], r["activity"], r["meal"], r["med"], r["condition"]
            )
    st.session_state["generated"] = residents_input
    st.session_state["report_date"] = report_date
    st.session_state["special"] = special
    st.session_state["home_name"] = home_name

if "generated" in st.session_state and st.session_state.get("home_name") == home_name:
    st.success("生成完了！文章を確認・編集してからPDFをダウンロードしてください。")

    edited_residents = []
    for r in st.session_state["generated"]:
        edited_text = st.text_area(
            f"{r['name']} さん　本日の様子",
            value=r["generated_text"],
            height=120,
            key=f"edit_{home_name}_{r['name']}",
        )
        r_copy = dict(r)
        r_copy["generated_text"] = edited_text
        edited_residents.append(r_copy)

    report_date = st.session_state["report_date"]
    weekday = WEEKDAYS[report_date.weekday()]
    special = st.session_state["special"]
    cfg = HOME_CONFIG[home_name]

    pdf_buf = build_pdf(report_date, weekday, cfg, edited_residents, special)

    filename = f"{cfg['file_prefix']} - {report_date.year}年{report_date.month}月{report_date.day}日.pdf"
    st.download_button(
        label="📥 PDFをダウンロード",
        data=pdf_buf,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )
