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
        "residents": ["細川隆希", "武長笑美"],
        "empty_slots": [],
        "day_staff": "",
        "night_staff": "坂口・寺岡",
        "recorder": "坂口　寺岡",
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
        "residents": ["館野真央", "小島勇人", "大塚蓮太", "大畑美奈"],
        "empty_slots": [],
        "day_staff": "",
        "night_staff": "伊藤・稲田",
        "recorder": "伊藤　稲田",
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


def generate_all_texts(residents_input):
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    client = anthropic.Anthropic(api_key=api_key)

    import random

    openings = [
        "起床後、", "本日は起床後、", "朝起きられた後、", "本日は朝から", "起床されると、",
        "本日は予定通り", "朝食を済ませた後、", "本日は日中、", "起床し身支度を整えた後、", "本日は活動的に",
    ]
    afternoon_focuses = [
        "帰宅後は自室で静かに読書などをして過ごされ",
        "帰宅後はリビングで他の入居者と談笑しながらくつろがれ",
        "帰宅後は特に外出することなくホーム内でゆったりと過ごされ",
        "帰宅後はテレビを観るなどして自分のペースでリラックスされ",
        "帰宅後は少し休憩を取られてから趣味の時間を楽しまれ",
        "帰宅後は洗濯や身の回りの整理をこなされ",
        "帰宅後はスタッフと会話を楽しみながら過ごされ",
        "帰宅後は音楽を聴くなどして穏やかに過ごされ",
    ]
    closings = [
        "夕食もしっかり召し上がり、入浴を済ませて就寝されました。",
        "食事・服薬ともに問題なく、そのまま静かに就寝されました。",
        "体調を崩される様子もなく、日課を滞りなくこなして就寝されました。",
        "気分も安定しており、穏やかな様子で一日を終えられました。",
        "特段の変化もなく、いつも通りの落ち着いた様子で就寝されました。",
        "夜も特に問題なく過ごされ、早めにお休みになりました。",
    ]

    residents_info = ""
    for i, r in enumerate(residents_input, 1):
        context = [f"昼間活動：{r['activity']}", f"体調：{r['condition']}"]
        meal_issues = [t for t, ok in r["meal"].items() if not ok]
        med_issues = [t for t, ok in r["med"].items() if not ok]
        if meal_issues:
            context.append(f"食事未摂取：{'/'.join(meal_issues)}")
        if med_issues:
            context.append(f"服薬未：{'/'.join(med_issues)}")
        hint = f"（書き出しヒント：『{random.choice(openings)}』／午後の表現ヒント：『{random.choice(afternoon_focuses)}』／締めのヒント：『{random.choice(closings)}』※そのまま使わず自然にアレンジしてよい）"
        residents_info += f"\n【{i}人目：{r['name']}さん】\n" + "\n".join(context) + f"\n{hint}\n"

    prompt = f"""グループホームの日報「本日の様子」欄の文章を、入居者ごとに書いてください。

{residents_info}

要件：
- 各入居者の文章の**書き出し・言い回し・語順・文構成をすべて変える**こと。テンプレートの使い回しは厳禁
- ヒントはあくまで参考。同じ表現を複数人に使い回さない
- 1人あたり3〜5文、敬体（〜されました、〜いたしました、〜されていました等）だが文末表現にもバリエーションを持たせる
- 活動内容→午後・帰宅後の様子→体調・気分→就寝、の流れは保ちつつ、順序や重み付けは人によって変えてよい
- 食事・服薬に×があれば自然に触れる、全て○なら無理に触れない
- 出力形式：各人の文章を「===」で区切って順番に出力（名前・見出し不要）
"""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1536,
        temperature=1.0,
        messages=[{"role": "user", "content": prompt}],
    )

    texts = msg.content[0].text.strip().split("===")
    texts = [t.strip() for t in texts if t.strip()]

    # 人数に合わせて補完
    while len(texts) < len(residents_input):
        texts.append("本日は終日穏やかにお過ごしになりました。体調・服薬ともに問題なく、就寝されました。")

    return texts


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
    staff_line = f"記録：{cfg['night_staff']}" if cfg.get("day_staff") == "" else f"日中：{cfg['day_staff']}　／　夜間：{cfg['night_staff']}"
    header_data = [[
        Paragraph(cfg["title"], style(13, bold=True, color=colors.white)),
        Paragraph(staff_line, style(9, color=colors.white, align="CENTER")),
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

# フォーム外で日付選択 — 変更を即時検知してリセット可能にする
report_date = st.date_input("日付", value=today, key=f"report_date_{home_name}")

# 日付またはホームが変わったら生成済み文章をリセット
_prev_date = st.session_state.get("report_date")
_prev_home = st.session_state.get("home_name")
if _prev_date is not None and (_prev_date != report_date or _prev_home != home_name):
    st.session_state.pop("generated", None)

st.markdown("---")

with st.form(f"report_form_{home_name}"):
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
            # 夕のみデフォルトONの利用者
            med_eve_only = ["小島勇人", "大塚蓮太"]
            med_default_m = name not in med_eve_only
            med_default_n = name not in med_eve_only
            med_m = dc1.checkbox("朝 ", value=med_default_m, key=f"dm_{home_name}_{name}")
            med_n = dc2.checkbox("昼 ", value=med_default_n, key=f"dn_{home_name}_{name}")
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
        texts = generate_all_texts(residents_input)
        for r, text in zip(residents_input, texts):
            r["generated_text"] = text
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
