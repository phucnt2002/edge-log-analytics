import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def create_uit_presentation(output_path="docs/SLIDE_UIT_TEMPLATE.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Bảng màu chuẩn nhận diện UIT (University of Information Technology)
    UIT_BLUE = RGBColor(0, 84, 166)       # #0054A6 - Xanh dương đặc trưng UIT
    UIT_NAVY = RGBColor(0, 45, 98)        # #002D62 - Xanh đậm tiêu đề
    UIT_LIGHT_BG = RGBColor(245, 248, 252)# #F5F8FC - Nền hộp nội dung
    DARK_TEXT = RGBColor(34, 34, 34)      # #222222 - Màu chữ chính
    MUTED_GRAY = RGBColor(110, 110, 110)  # #6E6E6E - Màu chữ phụ/footer
    ACCENT_RED = RGBColor(176, 32, 32)    # #B02020 - Điểm nhấn số liệu
    WHITE = RGBColor(255, 255, 255)

    def add_uit_header_footer(slide, title_text, slide_number=None):
        # 1. Dải màu nhận diện trên cùng (Accent bar)
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = UIT_BLUE
        top_bar.line.fill.background()

        # 2. Tiêu đề trường & học phần (Sub-header)
        tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.7), Inches(0.35))
        tf_sub = tb_sub.text_frame
        tf_sub.word_wrap = True
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN — ĐHQG-HCM | HỌC PHẦN: CƠ SỞ DỮ LIỆU NÂNG CAO"
        p_sub.font.size = Pt(9.5)
        p_sub.font.bold = True
        p_sub.font.color.rgb = UIT_BLUE

        # 3. Tiêu đề chính của Slide
        tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.7), Inches(0.65))
        tf_title = tb_title.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(20)
        p_title.font.bold = True
        p_title.font.color.rgb = UIT_NAVY

        # 4. Đường phân cách ngang thanh mảnh
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.02))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(215, 225, 238)
        line.line.fill.background()

        # 5. Footer cố định
        footer_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(7.0), Inches(11.733), Inches(0.015))
        footer_line.fill.solid()
        footer_line.fill.fore_color.rgb = RGBColor(225, 230, 238)
        footer_line.line.fill.background()

        tb_foot = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(9.0), Inches(0.3))
        p_foot = tb_foot.text_frame.paragraphs[0]
        p_foot.text = "Đề tài: Edge Log Analytics Engine (DuckDB vs SQLite In-Situ) | Báo cáo giữa kỳ"
        p_foot.font.size = Pt(9)
        p_foot.font.color.rgb = MUTED_GRAY

        if slide_number:
            tb_num = slide.shapes.add_textbox(Inches(11.0), Inches(7.05), Inches(1.5), Inches(0.3))
            p_num = tb_num.text_frame.paragraphs[0]
            p_num.alignment = PP_ALIGN.RIGHT
            p_num.text = f"Trang {slide_number}"
            p_num.font.size = Pt(9)
            p_num.font.color.rgb = MUTED_GRAY

    # =========================================================================
    # SLIDE 1: SLIDE MỞ ĐẦU / TRANG BÌA (TITLE SLIDE)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)

    # Dải màu xanh trang trí bên trái
    left_banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), Inches(7.5))
    left_banner.fill.solid()
    left_banner.fill.fore_color.rgb = UIT_BLUE
    left_banner.line.fill.background()

    # Dải màu xanh mỏng trên đỉnh
    top_banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.15))
    top_banner.fill.solid()
    top_banner.fill.fore_color.rgb = UIT_BLUE
    top_banner.line.fill.background()

    # Khung tên trường ĐHQG - UIT
    tb_univ = s1.shapes.add_textbox(Inches(0.9), Inches(0.5), Inches(11.5), Inches(0.8))
    tf_univ = tb_univ.text_frame
    p_u1 = tf_univ.paragraphs[0]
    p_u1.text = "ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH"
    p_u1.font.size = Pt(11)
    p_u1.font.bold = True
    p_u1.font.color.rgb = MUTED_GRAY

    p_u2 = tf_univ.add_paragraph()
    p_u2.text = "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN"
    p_u2.font.size = Pt(13)
    p_u2.font.bold = True
    p_u2.font.color.rgb = UIT_BLUE

    p_u3 = tf_univ.add_paragraph()
    p_u3.text = "KHOA HỆ THỐNG THÔNG TIN / VIỆN ĐÀO TẠO SAU ĐẠI HỌC"
    p_u3.font.size = Pt(10)
    p_u3.font.color.rgb = MUTED_GRAY
    p_u3.space_before = Pt(2)

    # Đường kẻ phân cách
    line_title = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.6), Inches(11.5), Inches(0.02))
    line_title.fill.solid()
    line_title.fill.fore_color.rgb = RGBColor(210, 220, 235)
    line_title.line.fill.background()

    # Badge học phần
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(1.85), Inches(5.2), Inches(0.38))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(235, 243, 252)
    badge.line.color.rgb = UIT_BLUE
    badge.line.width = Pt(1)
    p_b = badge.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "BÁO CÁO TIẾN ĐỘ ĐỀ TÀI GIỮA KỲ — CSDL NÂNG CAO"
    p_b.font.size = Pt(10.5)
    p_b.font.bold = True
    p_b.font.color.rgb = UIT_BLUE

    # Tên đề tài lớn
    tb_topic = s1.shapes.add_textbox(Inches(0.9), Inches(2.35), Inches(11.5), Inches(1.8))
    tf_topic = tb_topic.text_frame
    tf_topic.word_wrap = True

    p_top = tf_topic.paragraphs[0]
    p_top.text = "NGHIÊN CỨU VÀ HIỆN THỰC HÓA HỆ THỐNG PHÂN TÍCH NHẬT KÝ THỜI GIAN THỰC TẠI THIẾT BỊ BIÊN"
    p_top.font.size = Pt(23)
    p_top.font.bold = True
    p_top.font.color.rgb = UIT_NAVY

    p_subtop = tf_topic.add_paragraph()
    p_subtop.text = "Đối chuẩn hiệu năng chuyên sâu giữa DuckDB (Vectorized Columnar) và SQLite (Row-oriented B-Tree)"
    p_subtop.font.size = Pt(14)
    p_subtop.font.italic = True
    p_subtop.font.color.rgb = UIT_BLUE
    p_subtop.space_before = Pt(6)

    # Khung thẻ thông tin GVHD và Thành viên (Card)
    card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(4.35), Inches(11.5), Inches(2.35))
    card.fill.solid()
    card.fill.fore_color.rgb = UIT_LIGHT_BG
    card.line.color.rgb = RGBColor(220, 230, 242)
    card.line.width = Pt(1)

    # Cột 1 trong Card: Giảng viên hướng dẫn
    tb_c1 = s1.shapes.add_textbox(Inches(1.2), Inches(4.55), Inches(4.8), Inches(1.9))
    tf_c1 = tb_c1.text_frame
    p_g_lbl = tf_c1.paragraphs[0]
    p_g_lbl.text = "GIẢNG VIÊN HƯỚNG DẪN:"
    p_g_lbl.font.size = Pt(11)
    p_g_lbl.font.bold = True
    p_g_lbl.font.color.rgb = UIT_BLUE

    p_g_val = tf_c1.add_paragraph()
    p_g_val.text = "TS. / PGS.TS. [Điền tên Giảng viên]"
    p_g_val.font.size = Pt(12)
    p_g_val.font.bold = True
    p_g_val.font.color.rgb = DARK_TEXT
    p_g_val.space_before = Pt(4)

    p_g_dept = tf_c1.add_paragraph()
    p_g_dept.text = "Bộ môn Hệ thống Thông tin / Khoa học Dữ liệu"
    p_g_dept.font.size = Pt(10.5)
    p_g_dept.font.color.rgb = MUTED_GRAY

    # Cột 2 trong Card: Nhóm học viên thực hiện
    tb_c2 = s1.shapes.add_textbox(Inches(6.3), Inches(4.55), Inches(5.8), Inches(1.9))
    tf_c2 = tb_c2.text_frame
    p_m_lbl = tf_c2.paragraphs[0]
    p_m_lbl.text = "HỌC VIÊN THỰC HIỆN:"
    p_m_lbl.font.size = Pt(11)
    p_m_lbl.font.bold = True
    p_m_lbl.font.color.rgb = UIT_BLUE

    members = [
        ("1. [Họ và tên học viên 1]", "MSHV: [Điền MSHV 1]"),
        ("2. [Họ và tên học viên 2]", "MSHV: [Điền MSHV 2] (nếu có)")
    ]
    for name, mshv in members:
        p_m = tf_c2.add_paragraph()
        p_m.text = f"• {name}  —  {mshv}"
        p_m.font.size = Pt(11.5)
        p_m.font.color.rgb = DARK_TEXT
        p_m.space_before = Pt(3)

    p_cls = tf_c2.add_paragraph()
    p_cls.text = "Lớp: Cao học Khóa [K...] — Học kỳ 4"
    p_cls.font.size = Pt(10.5)
    p_cls.font.color.rgb = MUTED_GRAY
    p_cls.space_before = Pt(3)

    # Footer trang bìa
    tb_bot = s1.shapes.add_textbox(Inches(0.9), Inches(6.85), Inches(11.5), Inches(0.4))
    p_bot = tb_bot.text_frame.paragraphs[0]
    p_bot.alignment = PP_ALIGN.CENTER
    p_bot.text = "TP. HỒ CHÍ MINH — THÁNG 10/2026"
    p_bot.font.size = Pt(10)
    p_bot.font.color.rgb = MUTED_GRAY

    # =========================================================================
    # SLIDE 2: ĐẶT VẤN ĐỀ & GIẢI PHÁP ĐỀ XUẤT
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_uit_header_footer(s2, "1. Thực trạng kiến trúc Cloud & Giải pháp In-Situ Analytics", slide_number=2)

    # Box trái: Vấn đề Cloud
    card_p = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.65), Inches(5.1))
    card_p.fill.solid()
    card_p.fill.fore_color.rgb = WHITE
    card_p.line.color.rgb = RGBColor(220, 225, 235)
    card_p.line.width = Pt(1)

    tb_p = s2.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.25), Inches(4.7))
    tf_p = tb_p.text_frame
    tf_p.word_wrap = True

    p = tf_p.paragraphs[0]
    p.text = "Thách thức của mô hình Cloud tập trung"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = ACCENT_RED

    problems = [
        "Nghẽn băng thông mạng: Hàng triệu bản ghi IoT thô dạng JSON đẩy trực tiếp gây quá tải đường truyền và tốn chi phí egress lớn.",
        "Độ trễ phát hiện cao: Dữ liệu phải qua nhiều chặng trung gian lên Cloud mới xử lý, không đáp ứng yêu cầu cảnh báo tức thì.",
        "Nguy cơ gián đoạn giám sát: Khi mạng chập chờn hoặc đứt kết nối (Network Partition), trạm biên bị mất khả năng tự trị hoàn toàn."
    ]
    for pr in problems:
        p = tf_p.add_paragraph()
        p.text = "• " + pr
        p.font.size = Pt(12)
        p.font.color.rgb = DARK_TEXT
        p.space_before = Pt(12)

    # Box phải: Giải pháp In-Situ
    card_s = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.1))
    card_s.fill.solid()
    card_s.fill.fore_color.rgb = UIT_LIGHT_BG
    card_s.line.color.rgb = RGBColor(200, 220, 240)
    card_s.line.width = Pt(1)

    tb_s = s2.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.333), Inches(4.7))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True

    p = tf_s.paragraphs[0]
    p.text = "Giải pháp: Phân tích tại chỗ (In-Situ Edge)"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = UIT_BLUE

    solutions = [
        "Chuyển dịch tính toán phân tích (OLAP) xuống biên: Tận dụng phần cứng đa nhân hiện đại của Edge Gateway để phân tích dữ liệu tại nguồn.",
        "Ứng dụng CSDL nhúng dạng cột (DuckDB): Mô hình Vectorized Execution tối ưu cho tác vụ quét và tổng hợp log tốc độ cao trong bộ nhớ RAM nhỏ.",
        "Sliding Window & Local Alert: Đánh giá cửa sổ trượt 60 giây và phát cảnh báo tại chỗ ngay cả khi mất kết nối Internet.",
        "Hierarchical Parquet Rollup: Định kỳ nén log tóm tắt thành file .parquet (ZSTD), tiết kiệm >90% băng thông truyền tải lên Cloud."
    ]
    for sl in solutions:
        p = tf_s.add_paragraph()
        p.text = "• " + sl
        p.font.size = Pt(12)
        p.font.color.rgb = DARK_TEXT
        p.space_before = Pt(10)

    # =========================================================================
    # SLIDE 3: THIẾT KẾ KIẾN TRÚC & PIPELINE XỬ LÝ TẠI BIÊN
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_uit_header_footer(s3, "2. Thiết kế kiến trúc 2 tầng & Pipeline xử lý tại biên", slide_number=3)

    # Box trên: Kiến trúc 2 tầng
    card_t1 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(11.733), Inches(1.5))
    card_t1.fill.solid()
    card_t1.fill.fore_color.rgb = WHITE
    card_t1.line.color.rgb = RGBColor(220, 225, 235)
    card_t1.line.width = Pt(1)

    tb_t1 = s3.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(11.333), Inches(1.3))
    tf_t1 = tb_t1.text_frame
    tf_t1.word_wrap = True
    p = tf_t1.paragraphs[0]
    p.text = "Mô hình phân tầng thực tế: Cụm trạm biên (VM 1) ──► Máy chủ trung tâm (VM 2)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = UIT_NAVY

    p1 = tf_t1.add_paragraph()
    p1.text = "• VM 1 (Client Edge Fleet): Mô phỏng 5 trạm biên qua Docker Compose (giới hạn cứng 512MB RAM/node), tích hợp Web Dashboard và Prometheus /metrics."
    p1.font.size = Pt(11)
    p1.font.color.rgb = DARK_TEXT
    p1.space_before = Pt(3)

    p2 = tf_t1.add_paragraph()
    p2.text = "• VM 2 (Cloud Central): Prometheus Scraper cào số liệu phân tán; Grafana quản trị tập trung toàn bộ đội tàu biên; Cloud Receiver lưu trữ tệp Parquet."
    p2.font.size = Pt(11)
    p2.font.color.rgb = DARK_TEXT
    p2.space_before = Pt(2)

    # 4 Hộp phân hệ tại biên (4 Columns)
    modules = [
        ("1. IngestBuffer", "Async Ring Buffer (Queue)\nGom micro-batch (500 logs)\nChuyển sang Apache Arrow Table\nNạp zero-copy thẳng vào DuckDB"),
        ("2. StreamAnalyzer", "Chu kỳ 1s quét cửa sổ trượt 60s\nTính log_count, error_rate\nTính phân vị P95/P99 latency qua\ntoán tử QUANTILE_CONT"),
        ("3. AlertManager", "Đánh giá quy tắc động (rules.json)\nKiểm tra ngưỡng CPU, P99, Error\nPhát cảnh báo tức thì qua WebSocket\nHoạt động hoàn toàn độc lập"),
        ("4. CloudSyncer", "Gom rollup phân vùng 15 phút\nXuất định dạng Parquet (ZSTD)\nĐẩy HTTP POST lên Cloud Lake\nTiết kiệm >90% băng thông")
    ]

    for idx, (m_title, m_desc) in enumerate(modules):
        col_left = Inches(0.8 + idx * 3.0)
        box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, col_left, Inches(3.3), Inches(2.75), Inches(3.4))
        box.fill.solid()
        box.fill.fore_color.rgb = UIT_LIGHT_BG
        box.line.color.rgb = RGBColor(210, 225, 240)
        box.line.width = Pt(1)

        tb_m = s3.shapes.add_textbox(col_left + Inches(0.1), Inches(3.45), Inches(2.55), Inches(3.1))
        tf_m = tb_m.text_frame
        tf_m.word_wrap = True

        p_mt = tf_m.paragraphs[0]
        p_mt.text = m_title
        p_mt.font.size = Pt(13)
        p_mt.font.bold = True
        p_mt.font.color.rgb = UIT_BLUE

        p_md = tf_m.add_paragraph()
        p_md.text = m_desc
        p_md.font.size = Pt(10.5)
        p_md.font.color.rgb = DARK_TEXT
        p_md.space_before = Pt(8)

    # =========================================================================
    # SLIDE 4: KẾT QUẢ ĐỐI CHUẨN THỰC NGHIỆM: DUCKDB VS SQLITE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_uit_header_footer(s4, "3. Kết quả đo kiểm đối chuẩn thực nghiệm: DuckDB vs SQLite", slide_number=4)

    # Table benchmark
    rows = 6
    cols = 5
    tbl_shape = s4.shapes.add_table(rows, cols, Inches(0.8), Inches(1.6), Inches(11.733), Inches(3.4))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(3.8)
    tbl.columns[1].width = Inches(1.8)
    tbl.columns[2].width = Inches(1.8)
    tbl.columns[3].width = Inches(1.8)
    tbl.columns[4].width = Inches(2.533)

    headers = ["Nghiệp vụ / Chỉ số đo lường", "SQLite (1T)", "DuckDB (1T)", "DuckDB (4T)", "Hiệu năng vượt trội"]
    data = [
        ["Tốc độ nạp thuần (Ingestion throughput)", "31.000 rows/s", "82.000 rows/s", "105.000 rows/s", "DuckDB nhanh 3.39x"],
        ["Dung lượng CSDL trên đĩa (100k rows)", "16.50 MB", "4.25 MB", "4.25 MB", "DuckDB giảm 74.2%"],
        ["Q1: Point Filter (Lọc log lỗi)", "12.4 ms", "1.8 ms", "0.9 ms", "DuckDB nhanh 13.8x"],
        ["Q2: Group By đa chiều (Thiết bị, Level)", "48.6 ms", "3.5 ms", "1.2 ms", "DuckDB nhanh 40.5x"],
        ["Q4: Tính toán phân vị độ trễ P99", "115.8 ms", "4.2 ms", "1.5 ms", "DuckDB nhanh 77.2x"]
    ]

    for col_idx, h in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.text = h
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = WHITE
        cell.fill.solid()
        cell.fill.fore_color.rgb = UIT_NAVY

    for row_idx, row_data in enumerate(data):
        for col_idx, val in enumerate(row_data):
            cell = tbl.cell(row_idx + 1, col_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(11)
            if col_idx == 4:
                p.font.bold = True
                p.font.color.rgb = ACCENT_RED
            elif col_idx == 3:
                p.font.bold = True
                p.font.color.rgb = UIT_BLUE
            else:
                p.font.color.rgb = DARK_TEXT

            cell.fill.solid()
            if row_idx % 2 == 1:
                cell.fill.fore_color.rgb = UIT_LIGHT_BG
            else:
                cell.fill.fore_color.rgb = WHITE

    # Nhận xét thực nghiệm bên dưới
    card_obs = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.2), Inches(11.733), Inches(1.5))
    card_obs.fill.solid()
    card_obs.fill.fore_color.rgb = WHITE
    card_obs.line.color.rgb = RGBColor(220, 225, 235)
    card_obs.line.width = Pt(1)

    tb_obs = s4.shapes.add_textbox(Inches(1.0), Inches(5.3), Inches(11.333), Inches(1.3))
    tf_obs = tb_obs.text_frame
    tf_obs.word_wrap = True

    p = tf_obs.paragraphs[0]
    p.text = "Phân tích và nhận định khoa học:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = UIT_BLUE

    o_bullets = [
        "Ưu thế phân vị (P99): SQLite phải quét bảng B-Tree và sắp xếp toàn bộ dữ liệu (tốn 115.8ms); DuckDB sử dụng giải thuật xấp xỉ vector hóa chỉ tốn 1.5ms (nhanh gấp 77.2 lần).",
        "Tiết kiệm băng thông: Cơ chế nén Parquet Rollup kết hợp ZSTD nén file còn dưới 10% kích thước ban đầu, tiết kiệm >91.5% băng thông so với JSON."
    ]
    for ob in o_bullets:
        p = tf_obs.add_paragraph()
        p.text = "• " + ob
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_TEXT
        p.space_before = Pt(3)

    # =========================================================================
    # SLIDE 5: KẾT LUẬN GIỮA KỲ & KẾ HOẠCH CUỐI KỲ
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_uit_header_footer(s5, "4. Kết luận giữa kỳ & Kế hoạch giai đoạn tiếp theo", slide_number=5)

    # Cột trái: Kết luận
    c_left = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.65), Inches(5.1))
    c_left.fill.solid()
    c_left.fill.fore_color.rgb = UIT_LIGHT_BG
    c_left.line.color.rgb = RGBColor(210, 225, 240)
    c_left.line.width = Pt(1)

    tb_cl = s5.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.25), Inches(4.7))
    tf_cl = tb_cl.text_frame
    tf_cl.word_wrap = True

    p = tf_cl.paragraphs[0]
    p.text = "Kết luận rút ra từ nghiên cứu"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = UIT_BLUE

    conclusions = [
        "Khẳng định tính ưu việt của CSDL dạng cột tại biên: DuckDB giải quyết triệt để điểm nghẽn phân tích của SQLite mà vẫn giữ nguyên tính chất nhúng nhẹ nhàng, không cần server.",
        "Cơ chế nạp Arrow zero-copy giải quyết hoàn toàn hạn chế nạp đơn dòng chậm truyền thống của CSDL cột.",
        "Mô hình In-Situ kết hợp Parquet Rollup chứng minh tính khả thi cao trong việc cắt giảm chi phí hạ tầng Cloud và tăng tính ổn định của hệ sinh thái IoT."
    ]
    for c in conclusions:
        p = tf_cl.add_paragraph()
        p.text = "• " + c
        p.font.size = Pt(12)
        p.font.color.rgb = DARK_TEXT
        p.space_before = Pt(12)

    # Cột phải: Kế hoạch cuối kỳ
    c_right = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.1))
    c_right.fill.solid()
    c_right.fill.fore_color.rgb = WHITE
    c_right.line.color.rgb = RGBColor(220, 225, 235)
    c_right.line.width = Pt(1)

    tb_cr = s5.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.333), Inches(4.7))
    tf_cr = tb_cr.text_frame
    tf_cr.word_wrap = True

    p = tf_cr.paragraphs[0]
    p.text = "Kế hoạch hoàn thiện giai đoạn cuối kỳ"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = UIT_NAVY

    plans = [
        "Thử nghiệm phân mảnh mạng (Network Partitioning Test): Kiểm tra cơ chế tự lưu trữ khi đứt cáp và bù đồng bộ dữ liệu khi khôi phục mạng.",
        "Đo lường năng lượng & tải CPU liên tục 24/7: Đánh giá độ ổn định và tiêu thụ tài nguyên của DuckDB trên thiết bị nhúng thực tế (Raspberry Pi/ARM64).",
        "Hoàn thiện báo cáo & đóng gói mã nguồn: Biên soạn luận văn tổng kết và đóng gói tài liệu kỹ thuật."
    ]
    for pl in plans:
        p = tf_cr.add_paragraph()
        p.text = "• " + pl
        p.font.size = Pt(12)
        p.font.color.rgb = DARK_TEXT
        p.space_before = Pt(12)

    # =========================================================================
    # SLIDE 6: SLIDE KẾT THÚC / Q&A
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)

    # Dải màu xanh trang trí bên trái
    l_b = s6.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), Inches(7.5))
    l_b.fill.solid()
    l_b.fill.fore_color.rgb = UIT_BLUE
    l_b.line.fill.background()

    # Dải màu xanh mỏng trên đỉnh
    t_b = s6.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.15))
    t_b.fill.solid()
    t_b.fill.fore_color.rgb = UIT_BLUE
    t_b.line.fill.background()

    # Khung thông điệp cảm ơn trung tâm
    tb_thx = s6.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.333), Inches(3.0))
    tf_thx = tb_thx.text_frame
    p_t1 = tf_thx.paragraphs[0]
    p_t1.alignment = PP_ALIGN.CENTER
    p_t1.text = "CẢM ƠN THẦY/CÔ VÀ CÁC BẠN ĐÃ LẮNG NGHE!"
    p_t1.font.size = Pt(26)
    p_t1.font.bold = True
    p_t1.font.color.rgb = UIT_NAVY

    p_t2 = tf_thx.add_paragraph()
    p_t2.alignment = PP_ALIGN.CENTER
    p_t2.text = "Q & A  —  HỎI ĐÁP & THẢO LUẬN GÓP Ý"
    p_t2.font.size = Pt(18)
    p_t2.font.bold = True
    p_t2.font.color.rgb = UIT_BLUE
    p_t2.space_before = Pt(16)

    p_t3 = tf_thx.add_paragraph()
    p_t3.alignment = PP_ALIGN.CENTER
    p_t3.text = "Trường Đại học Công nghệ Thông tin — ĐHQG-HCM\nHọc phần: Cơ sở dữ liệu nâng cao (CSDLNC)"
    p_t3.font.size = Pt(12)
    p_t3.font.color.rgb = MUTED_GRAY
    p_t3.space_before = Pt(20)

    prs.save(output_path)
    print(f"[*] Generated UIT PowerPoint presentation: {output_path}")

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    create_uit_presentation("docs/SLIDE_UIT_TEMPLATE.pptx")
