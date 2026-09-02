# -*- coding: utf-8 -*-
"""Презентация лабораторной на шаблоне ИТМО.

Мастер, макеты и фоны берутся из дипломной презентации. Каждый макет шаблона —
цветная рамка с белым «окном»: фиолетовая, голубая, красная. Обложка — тёмный
фон с логотипом, он задаётся на самом слайде, а не в макете.
"""
import copy
import os
import sys
import tempfile
import zipfile

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches, Pt

TEMPLATE = "C:/Users/79101/Desktop/Диплом/Презентация_Халеев_М_Д.pptx"
IMG = "C:/Users/79101/Downloads/Лаба_заправки/slides_img"
OUT = "C:/Users/79101/Downloads/Лаба_заправки/Лаба_заправки.pptx"

PURPLE = RGBColor(0x93, 0x07, 0xFE)
CYAN = RGBColor(0x00, 0x8C, 0xB4)      # затемнён, чтобы читался на белом
RED = RGBColor(0xD9, 0x2B, 0x22)
INK = RGBColor(0x1A, 0x1A, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

L_TITLE, L_PURPLE, L_CYAN, L_TWO, L_FINAL = 0, 9, 9, 9, 9
TITLE_PT = 24

# белое «окно» макета: x 0.47..9.53, y 1.06..5.08 дюйма
CARD = (0.6, 1.2, 9.4, 5.0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

prs = Presentation(TEMPLATE)


# ------------------------------------------------- достаём обложку из шаблона
def cover_image_path():
    """Картинка, которой залит фон титульного слайда шаблона."""
    slide = list(prs.slides)[0]
    bg = slide.element.find(qn("p:cSld")).find(qn("p:bg"))
    if bg is None:
        return None
    blip = bg.find(".//" + qn("a:blip"))
    if blip is None:
        return None
    rid = blip.get(qn("r:embed"))
    part = slide.part.rels[rid].target_part
    path = os.path.join(tempfile.gettempdir(), "itmo_cover" +
                        os.path.splitext(str(part.partname))[1])
    with open(path, "wb") as f:
        f.write(part.blob)
    return path


COVER = cover_image_path()

# --- запоминаем номер слайда из шаблона
page_no_proto = None
for slide in prs.slides:
    for sh in slide.shapes:
        if not sh.is_placeholder and sh.has_text_frame and sh.text_frame.text.strip().isdigit():
            page_no_proto = copy.deepcopy(sh._element)
            break
    if page_no_proto is not None:
        break

# --- чистим слайды шаблона, мастер и тема остаются
sld_id_lst = prs.slides._sldIdLst
for sld_id in list(sld_id_lst):
    prs.part.drop_rel(sld_id.rId)
    sld_id_lst.remove(sld_id)


def set_background(slide, image_path):
    image_part, rid = slide.part.get_or_add_image_part(image_path)
    bg = parse_xml(
        f'<p:bg {nsdecls("p", "a", "r")}><p:bgPr>'
        f'<a:blipFill dpi="0" rotWithShape="1"><a:blip r:embed="{rid}"><a:lum/></a:blip>'
        f'<a:srcRect/><a:stretch><a:fillRect/></a:stretch></a:blipFill>'
        f'<a:effectLst/></p:bgPr></p:bg>')
    slide.element.find(qn("p:cSld")).insert(0, bg)


def fill(tf, items):
    """items: строка либо dict(t=текст, size=, color=, bold=, level=, space=)."""
    tf.clear()
    for i, item in enumerate(items):
        d = {"t": item} if isinstance(item, str) else dict(item)
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.level = d.get("level", 0)
        if d.get("space"):
            para.space_before = Pt(d["space"])
        run = para.add_run()
        run.text = d["t"]
        if d.get("size"):
            run.font.size = Pt(d["size"])
        if d.get("color") is not None:
            run.font.color.rgb = d["color"]
        if d.get("bold"):
            run.font.bold = True


def ph_by_idx(slide, idx):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            return ph
    return None


FRAMED = None   # заполняется ниже: макеты с цветной рамкой


def new_slide(layout_idx, title, title_color=None):
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[layout_idx])
    if title_color is None and layout_idx in (L_PURPLE, L_CYAN, L_TWO, L_FINAL):
        title_color = WHITE          # заголовок стоит на цветной рамке
    if slide.shapes.title is not None and title is not None:
        tf = slide.shapes.title.text_frame
        tf.clear()
        run = tf.paragraphs[0].add_run()
        run.text = title
        run.font.size = Pt(TITLE_PT)
        if title_color is not None:
            run.font.color.rgb = title_color
    return slide


def stamp_page_no(slide):
    if page_no_proto is None:
        return
    el = copy.deepcopy(page_no_proto)
    slide.shapes._spTree.append(el)
    for sh in slide.shapes:
        if sh._element is el and sh.has_text_frame:
            for para in sh.text_frame.paragraphs:
                for run in para.runs:
                    run.text = str(len(prs.slides._sldIdLst))
                break


def add(layout_idx, title, items, body_box=None, picture=None, pic_box=None):
    slide = new_slide(layout_idx, title)
    body = None
    for ph in slide.placeholders:
        if ph.placeholder_format.idx != 0:
            body = ph
            break
    if body is not None:
        if items:
            fill(body.text_frame, items)
            if body_box:
                body.left, body.top = Inches(body_box[0]), Inches(body_box[1])
                body.width, body.height = Inches(body_box[2]), Inches(body_box[3])
        else:
            body._element.getparent().remove(body._element)
    if picture:
        path = os.path.join(IMG, picture)
        iw, ih = Image.open(path).size
        x, y, w = pic_box
        slide.shapes.add_picture(path, Inches(x), Inches(y),
                                 width=Inches(w), height=Inches(w * ih / iw))
    stamp_page_no(slide)
    return slide


def add_two(title, left, right, layout_idx=None):
    """Две колонки внутри белого поля макета."""
    slide = new_slide(layout_idx or L_PURPLE, title)
    for ph in list(slide.placeholders):
        if ph.placeholder_format.idx != 0:
            ph._element.getparent().remove(ph._element)

    accent = CYAN if (layout_idx or L_PURPLE) == L_CYAN else PURPLE
    for (header, lines), x in ((left, 0.75), (right, 5.15)):
        box = slide.shapes.add_textbox(Inches(x), Inches(1.7), Inches(4.0), Inches(3.0))
        box.text_frame.word_wrap = True
        fill(box.text_frame,
             [{"t": header, "size": 19, "bold": True, "color": accent}] +
             [{"t": t, "size": 15, "space": 8} for t in lines])
    stamp_page_no(slide)
    return slide


def stat(number, caption, color=None):
    """Крупное число и мелкая подпись под ним."""
    return [
        {"t": number, "size": 26, "color": color or PURPLE, "bold": True, "space": 10},
        {"t": caption, "size": 12, "color": INK},
    ]


def add_two_pics(title, layout_idx, left, right):
    """Слайд с двумя картинками и подписями."""
    slide = new_slide(layout_idx, title)
    for ph in list(slide.placeholders):
        if ph.placeholder_format.idx != 0:
            ph._element.getparent().remove(ph._element)

    accent = CYAN if layout_idx == L_CYAN else PURPLE
    for (header, picture, note), x in ((left, 0.55), (right, 5.05)):
        box = slide.shapes.add_textbox(Inches(x), Inches(1.35), Inches(4.2), Inches(0.4))
        box.text_frame.word_wrap = True
        fill(box.text_frame, [{"t": header, "size": 17, "bold": True, "color": accent}])

        path = os.path.join(IMG, picture)
        iw, ih = Image.open(path).size
        slide.shapes.add_picture(path, Inches(x), Inches(1.85),
                                 width=Inches(4.2), height=Inches(4.2 * ih / iw))

        box = slide.shapes.add_textbox(Inches(x), Inches(3.85), Inches(4.2), Inches(0.9))
        box.text_frame.word_wrap = True
        fill(box.text_frame, [{"t": note, "size": 14}])
    stamp_page_no(slide)
    return slide


# ================================================================== титул
slide = new_slide(L_TITLE, None)
for ph in list(slide.placeholders):
    ph._element.getparent().remove(ph._element)
if COVER:
    set_background(slide, COVER)

box = slide.shapes.add_textbox(Inches(0.9), Inches(2.6), Inches(8.2), Inches(1.2))
fill(box.text_frame, [{"t": "Детекция заправок\nпо датчику уровня топлива",
                       "size": 30, "color": WHITE, "bold": True}])
box.text_frame.word_wrap = True

box = slide.shapes.add_textbox(Inches(0.9), Inches(4.05), Inches(8.2), Inches(0.9))
fill(box.text_frame, [
    {"t": "Лабораторная работа", "size": 16, "color": WHITE},
    {"t": "50 машин · 6.1 млн сообщений телематики · июль — декабрь 2025",
     "size": 13, "color": RGBColor(0xC9, 0xC9, 0xC9)},
])

import slides_content

slides_content.build({
    "add": add, "add_two_pics": add_two_pics, "add_two": add_two,
    "stat": stat, "new_slide": new_slide, "fill": fill,
    "stamp_page_no": stamp_page_no, "prs": prs,
    "L_PURPLE": L_PURPLE, "PURPLE": PURPLE, "INK": INK, "WHITE": WHITE,
})

prs.save(OUT)
print(f"сохранено: {OUT}")
print(f"слайдов: {len(prs.slides._sldIdLst)}")
print(f"обложка: {COVER}")
