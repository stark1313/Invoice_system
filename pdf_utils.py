# PDF generation for napum, cheonggu, gyeonjeok
import os
from io import BytesIO
from utils import amount_to_korean_won
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _gyeonjeok_cell_content(text, font_name, col_width_mm, base_font=7, min_font=5):
    """22자 초과 시 6pt, 30자 초과 시 5pt로 1줄 유지. min_font: 주소는 6으로 조금 크게"""
    s = (text or "-").strip()
    if not s:
        return "-"
    try:
        col_pt = col_width_mm * (72 / 25.4)
        w = pdfmetrics.stringWidth(s, font_name, base_font)
        if w <= col_pt - 20:
            return s
        for fs in range(base_font - 1, min_font - 1, -1):
            w = pdfmetrics.stringWidth(s, font_name, fs)
            if w <= col_pt - 20:
                return Paragraph(s, ParagraphStyle("", fontName=font_name, fontSize=fs, leading=fs+1))
    except Exception:
        pass
    if len(s) > 30:
        return Paragraph(s, ParagraphStyle("", fontName=font_name, fontSize=min_font, leading=min_font+1))
    if len(s) > 22:
        return Paragraph(s, ParagraphStyle("", fontName=font_name, fontSize=6, leading=7))
    return s


class _StampOverlay(Flowable):
    """행 높이 변경 없이 직인을 오버레이로 그리는 Flowable"""
    def __init__(self, stamp_path, w, h):
        self.stamp_path = stamp_path
        self.w, self.h = w, h
    def wrap(self, availWidth, availHeight):
        return 0, 0
    def draw(self):
        from reportlab.lib.utils import ImageReader
        self.canv.saveState()
        self.canv.translate(112*mm, 262*mm)
        self.canv.drawImage(ImageReader(self.stamp_path), 0, 0, width=self.w, height=self.h, mask='auto')
        self.canv.restoreState()


def _register_font():
    try:
        pdfmetrics.registerFont(TTFont("Malgun", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"))
        return "Malgun"
    except Exception:
        pass
    try:
        pdfmetrics.registerFont(TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf"))
        return "Malgun"
    except Exception:
        pass
    return "Helvetica"


def build_napum_pdf(transaction, customer, rows, total_amount, supplier=None, show_stamp=False, title="납  품  서", footer_text="상기와 같이 납품하였기에 납품서를 제출합니다.", include_bank_info=False):
    """납품서 PDF - 상세표만, 하단 문구+회사정보"""
    supplier = supplier or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)
    font_name = _register_font()
    story = []

    title_para = Paragraph(f"<b>{title}</b>", ParagraphStyle("Title", fontName=font_name, fontSize=20, alignment=1))
    total_korean = amount_to_korean_won(total_amount)
    d = transaction.transaction_date

    # 공사명/금액 헤더
    w3 = 35*mm / 3
    w_colon, w_val = 8*mm, 180*mm - 35*mm - 8*mm
    napum_header_data = [
        ["공", "사", "명", ":   ", (transaction.project_name or "")],
        ["금", "", "액", ":   ", f"₩ {total_amount:,}원 ({total_korean})"],
    ]
    t_header = Table(napum_header_data, colWidths=[w3, w3, w3, w_colon, w_val])
    t_header.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (2, 0), "CENTER"), ("ALIGN", (0, 1), (0, 1), "CENTER"), ("ALIGN", (2, 1), (2, 1), "CENTER"),
    ]))

    # 상세표 (빈행 10줄)
    row_h = 5*mm
    table_data = [["품명", "규격", "수량", "단위", "단가", "금액", "비고"]]
    for r in rows:
        unit_p = (r["total"] // r["quantity"]) if r.get("quantity") else 0
        name_cell = _gyeonjeok_cell_content(r.get("name"), font_name, 35)
        spec_cell = _gyeonjeok_cell_content(r.get("spec"), font_name, 35)
        table_data.append([name_cell, spec_cell, str(r["quantity"]), (r.get("unit") or "EA")[:6], f"{unit_p:,}원", f"{r['total']:,}원", ""])
    blank_count = max(0, min(6 - len(rows), 6))  # 이하여백 밑 빈행 6줄 (1페이지 맞춤)
    if blank_count > 0:
        table_data.append(["", "이", "하", "여", "백", "", ""])
        for _ in range(blank_count - 1):
            table_data.append(["", "", "", "", "", "", ""])
    table_data.append(["", "", "", "", "합계 (VAT 포함)", f"{total_amount:,}원", ""])

    cols = [35*mm, 35*mm, 15*mm, 15*mm, 20*mm, 30*mm, 30*mm]
    t_detail = Table(table_data, colWidths=cols, rowHeights=[row_h]*len(table_data))
    style_list = [
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 1*mm), ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5*mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("GRID", (0, 0), (-1, -2), 1, colors.black), ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (3, -1), "CENTER"), ("ALIGN", (4, 0), (5, -1), "RIGHT"),
        ("ALIGN", (0, -1), (4, -1), "CENTER"),
    ]
    data_start = 1 + len(rows)
    if blank_count > 0:
        style_list.append(("ALIGN", (1, data_start), (1, data_start), "RIGHT"))
        style_list.append(("ALIGN", (4, data_start), (4, data_start), "LEFT"))
    t_detail.setStyle(TableStyle(style_list))

    # 하단 문구 (가운데)
    footer_para = Paragraph(footer_text, ParagraphStyle("", fontName=font_name, fontSize=10, alignment=1))
    story.append(Spacer(1, 4*mm))

    # 회사정보 (날짜 1/2/3열 병합 왼쪽정렬, 1열 5글자, : 가운데, 3열 왼쪽)
    date_str = f"{d.year}년   {d.month}월   {d.day}일" if d else ""
    info_data = [
        [date_str, "", ""],
        ["사업자번호", ":", supplier.get('biz_no') or ''],
        ["주   소", ":", supplier.get('address') or ''],
        ["상   호", ":", supplier.get('name') or ''],
        ["대   표", ":", supplier.get('ceo') or ''],
    ]
    t_info = Table(info_data, colWidths=[15*mm, 4*mm, 89*mm])
    t_info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("SPAN", (0, 0), (2, 0)),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"), ("ALIGN", (1, 1), (1, -1), "CENTER"), ("ALIGN", (2, 1), (2, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    # 프레임: 제목, 헤더, 상세표
    frame_data = [[title_para], [t_header], [t_detail]]
    t_frame = Table(frame_data, colWidths=[180*mm])
    t_frame.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2*mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
        ("BOTTOMPADDING", (0, 0), (0, 0), 8*mm), ("BOTTOMPADDING", (0, 1), (0, 1), 4*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 2*mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2*mm),
        ("BOTTOMPADDING", (0, 2), (0, 2), 0),
    ]))
    story.append(t_frame)
    story.append(Spacer(1, 4*mm))
    if include_bank_info:
        bank_lines = [
            f"은행 : {supplier.get('bank') or ''}",
            f"예금주 : {supplier.get('account_holder') or ''}",
            f"계좌번호 : {supplier.get('account_no') or ''}",
        ]
        bank_para = Paragraph("<br/>".join(bank_lines), ParagraphStyle("", fontName=font_name, fontSize=9, alignment=0, leading=11))
        story.append(bank_para)
        story.append(Spacer(1, 4*mm))
    story.append(footer_para)
    story.append(Spacer(1, 6*mm))
    t_info_wrap = Table([[t_info]], colWidths=[180*mm])
    t_info_wrap.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "RIGHT")]))
    story.append(t_info_wrap)
    # 거래처 대표자명 맨 아래 (30pt, 왼쪽정렬, 글자마다 공백 4칸)
    ceo_name = getattr(customer, 'ceo', None) or ''
    ceo_spaced = '    '.join(list(ceo_name))
    ceo_para = Paragraph(ceo_spaced, ParagraphStyle("", fontName=font_name, fontSize=30, alignment=0, leading=36))
    story.append(Spacer(1, 8*mm))
    story.append(ceo_para)
    doc.build(story)
    buf.seek(0)
    return buf


def build_cheonggu_pdf(transaction, customer, rows, total_amount, supplier=None, show_stamp=False):
    """청구서 PDF - 납품서와 동일 양식 (제목만 청구서)"""
    return build_napum_pdf(transaction, customer, rows, total_amount, supplier, show_stamp=show_stamp, title="청  구  서", footer_text="상기와 같이 청구합니다.", include_bank_info=True)


def build_gyeonjeok_pdf(transaction, customer, rows, total_supply, total_amount, supplier=None, show_stamp=False, title="견  적  서", recipient_ceo_only=False, detail_first=False):
    """견적서 PDF - 원본 견적서 양식 (1페이지, 진한 선, 공급자/공급받는자 표)"""
    supplier = supplier or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)
    font_name = _register_font()
    story = []

    title_para = Paragraph(f"<b>{title}</b>", ParagraphStyle("Title", fontName=font_name, fontSize=20, alignment=1))
    d = transaction.transaction_date

    total_korean = amount_to_korean_won(total_amount)
    amount_para = Paragraph(f"아래와 같이 견적합니다.<br/>합계금액 : {total_amount:,}원 ({total_korean})", ParagraphStyle("", fontName=font_name, fontSize=7, leading=10, alignment=1))
    name_ceo = f"{(supplier.get('name') or '-')} / {(supplier.get('ceo') or '-')}"[:18]

    # 위표 - 7pt, 사업장주소/업태종목/소재지는 2줄 예상 시 해당 셀만 글자축소
    # 공급받는자 100mm(라벨20+데이터80), 공급자 80mm(라벨20+데이터60)
    addr_supplier_cell = _gyeonjeok_cell_content(supplier.get("address"), font_name, 60, min_font=6)  # 소재지 조금 크게
    biz_cell = _gyeonjeok_cell_content(supplier.get("business_type"), font_name, 60)
    date_cell = f"{d.year}년  {d.month}월  {d.day}일" if d else ""
    contact_cell = _gyeonjeok_cell_content(f"{(supplier.get('phone') or '-')} / {(supplier.get('fax') or '-')}", font_name, 60)
    gongsa_cell = _gyeonjeok_cell_content(f"공사명 : {transaction.project_name or '-'}", font_name, 80, base_font=9, min_font=7)
    recipient_cell = (customer.ceo or "") if recipient_ceo_only else f"{(customer.name or '')} 귀하"
    recipient_para = Paragraph(f"<b>{recipient_cell}</b>", ParagraphStyle("", fontName=font_name, fontSize=9))
    info_data = [
        [date_cell, date_cell, "공급자", "공급자"],
        [recipient_para, recipient_para, "사업자번호", (supplier.get("biz_no") or "-")[:14]],
        [gongsa_cell, gongsa_cell, "상호/대표", name_ceo],
        ["", "", "주소", addr_supplier_cell],
        [amount_para, "", "업태/종목", biz_cell],
        ["", "", "연락처", contact_cell],
    ]
    info_row_h = 6*mm
    t_info = Table(info_data, colWidths=[20*mm, 80*mm, 20*mm, 60*mm], rowHeights=[info_row_h]*6)
    t_info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("FONTSIZE", (0, 0), (1, 2), 9),  # 날짜·귀하·공사명 글자 크게
        ("LEFTPADDING", (0, 0), (-1, -1), 1*mm), ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5*mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("LINEBELOW", (0, 0), (1, 0), 0, colors.black),  # 날짜 아래
        ("LINEBELOW", (0, 1), (1, 1), 0, colors.black),  # 상호명 아래
        ("LINEBELOW", (0, 2), (1, 2), 0, colors.black),  # 공사명 아래
        ("LINEBELOW", (0, 3), (1, 3), 0, colors.black),  # 빈행 아래
        ("LINEBELOW", (0, 4), (1, 4), 0, colors.black),  # 아래와같이 견적합니다 위
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (2, 0), (3, 0)),
        ("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 2), (1, 2)), ("SPAN", (0, 3), (1, 3)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("SPAN", (0, 4), (1, 5)), ("VALIGN", (0, 4), (1, 5), "MIDDLE"), ("ALIGN", (0, 4), (1, 5), "LEFT"),
        ("ALIGN", (0, 0), (1, 0), "LEFT"),   # 날짜 왼쪽 정렬
        ("ALIGN", (0, 2), (1, 2), "CENTER"),  # 공사명 가운데
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]))

    # 아래표(상세) - 원래 열 너비 유지, 규격은 2줄 예상 시 글자축소
    row_h = 5*mm
    table_data = [["품명", "규격", "수량", "단위", "단가", "금액", "비고"]]
    for r in rows:
        unit_p = (r["total"] // r["quantity"]) if r.get("quantity") else 0
        name_cell = _gyeonjeok_cell_content(r.get("name"), font_name, 35)
        spec_cell = _gyeonjeok_cell_content(r.get("spec"), font_name, 35)
        table_data.append([name_cell, spec_cell, str(r["quantity"]), (r.get("unit") or "EA")[:6], f"{unit_p:,}원", f"{r['total']:,}원", ""])
    blank_count = max(0, min(15 - len(rows), 15))  # 기본 빈 행 15줄 (이하 여백 + 14)
    if blank_count > 0:
        table_data.append(["", "이", "하", "여", "백", "", ""])
        for _ in range(blank_count - 1):
            table_data.append(["", "", "", "", "", "", ""])
    table_data.append(["", "", "", "", "합계 (VAT 포함)", f"{total_amount:,}원", ""])

    # 상세표: 품명35 규격35 수량15 단위15 단가20 공급가액30 비고30 (총180mm)
    cols = [35*mm, 35*mm, 15*mm, 15*mm, 20*mm, 30*mm, 30*mm]
    t = Table(table_data, colWidths=cols, rowHeights=[row_h]*len(table_data))
    style_list = [
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("FONTSIZE", (0, 1), (-1, -3), 7),  # 상세 데이터 행 (수량·단위 가독성)
        ("LEFTPADDING", (0, 0), (-1, -1), 1*mm), ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5*mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("GRID", (0, 0), (-1, -2), 1, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (3, -1), "CENTER"),  # 품명·규격·수량·단위 가운데
        ("ALIGN", (4, 0), (5, -1), "RIGHT"),
        ("ALIGN", (0, -1), (4, -1), "CENTER"),   # 합계 행 가운데
    ]
    data_start = 1 + len(rows)
    if blank_count > 0:
        style_list.append(("ALIGN", (1, data_start), (1, data_start), "RIGHT"))   # 이 - 오른쪽
        style_list.append(("ALIGN", (4, data_start), (4, data_start), "LEFT"))     # 백 - 왼쪽
    t.setStyle(TableStyle(style_list))

    if detail_first:
        # 납품서: 공사명/금액 표 위에, 제목-표 거리 3줄
        # 납품서: 공사명 3등분, 금액 2등분, : 뒤 공백 3칸
        w3 = 35*mm / 3  # 공/사/명 각 1/3
        w_colon = 8*mm
        w_val = 180*mm - 35*mm - w_colon
        napum_row1 = ["공", "사", "명", ":   ", (transaction.project_name or "")]
        napum_row2 = ["금", "", "액", ":   ", f"₩ {total_amount:,}원 ({total_korean})"]
        t_napum_header = Table(
            [napum_row1, napum_row2],
            colWidths=[w3, w3, w3, w_colon, w_val]
        )
        t_napum_header.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (2, 0), "CENTER"),
            ("ALIGN", (0, 1), (0, 1), "CENTER"),
            ("ALIGN", (2, 1), (2, 1), "CENTER"),
        ]))
        napum_header = t_napum_header
        frame_rows = [[title_para], [napum_header], [t], [t_info]]
        frame_style = [
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 0), (0, 0), 8*mm),  # 제목-표 사이 여백
            ("BOTTOMPADDING", (0, 1), (0, 1), 4*mm),  # 공사명/금액 아래 3줄 정도
            ("LEFTPADDING", (0, 0), (-1, -1), 2*mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 2), (0, 2), 0),
            ("TOPPADDING", (0, 3), (0, 3), 0),
        ]
    else:
        frame_rows = [[title_para], [t_info], [t]]
        frame_style = [
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 0), (0, 0), 8*mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 2*mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2*mm),
            ("BOTTOMPADDING", (0, 1), (0, 1), 0),
            ("TOPPADDING", (0, 2), (0, 2), 0),
        ]
    t_frame = Table(frame_rows, colWidths=[180*mm])
    t_frame.setStyle(TableStyle(frame_style))
    story.append(t_frame)
    if show_stamp and supplier.get("stamp_path") and os.path.isfile(supplier["stamp_path"]):
        story.append(_StampOverlay(supplier["stamp_path"], 12*mm, 12*mm))
    doc.build(story)
    buf.seek(0)
    return buf
