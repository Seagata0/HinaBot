import os, re
from datetime import date
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BLUE_ARCHIVE_COLOR = HexColor("#0098e6")
DARK_BLUE_COLOR = HexColor("#003c7d")
BACKGROUND_COLOR = HexColor("#f0f4f7")

try:
    pdfmetrics.registerFont(TTFont('Archive', 'Archive.ttf'))
    FontHeader = "Archive"
    pdfmetrics.registerFont(TTFont('NotoSans', 'NotoSans.ttf'))
    HFont = 'NotoSans'
except Exception:
    print("Warning: One of the font is missing")
    FontHeader = "Helvetica"
    HFont = 'Helvetica-Bold'

class HorizontalRule(Flowable):
    """
    A simple horizontal line flowable.
    """
    def __init__(self, width, color=black, thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.thickness = thickness

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

def create_mission_brief_template(canvas: canvas.Canvas, doc):
    """
    Draws the static elements of the template on each page.
    """
    canvas.saveState()
    page_width, page_height = doc.pagesize

    canvas.setFillColor(BACKGROUND_COLOR)
    canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    header_height = 2.5 * cm
    header_y = page_height - header_height
    canvas.setFillColor(BLUE_ARCHIVE_COLOR)
    canvas.rect(0, header_y, page_width, header_height, fill=1, stroke=0)

    logo_path = 'logo.png'
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        logo_width, logo_height = logo.getSize()
        aspect = logo_height / float(logo_width)
        logo_display_height = header_height * 0.8
        logo_display_width = logo_display_height / aspect
        canvas.drawImage(logo, 2 * cm, header_y + (header_height - logo_display_height) / 2,
                       width=logo_display_width, height=logo_display_height, mask='auto')

    canvas.setFont(FontHeader, 24.5)
    canvas.setFillColor(white)
    canvas.drawString(4.25 * cm, header_y + 1.25 * cm, "OPERATIONAL DIRECTIVE")
    canvas.setFont(FontHeader, 10.49)
    canvas.drawString(4.25 * cm, header_y + 0.8 * cm, "S.C.H.A.L.E // Independent Federal Investigation Club")

    footer_text = f"DOCUMENT PAGE {canvas.getPageNumber()} // FOR SEAGATA-SENSEI ONLY"
    canvas.setFont('Helvetica-Oblique', 8)
    canvas.setFillColor(DARK_BLUE_COLOR)
    canvas.drawCentredString(page_width / 2, 1.5 * cm, footer_text)

    canvas.restoreState()

def parse_md_to_story(md_content, doc_width):
    """
    Parses markdown content, including headers (H1-H5) and tables,
    into a ReportLab 'story' list.
    """

    story = []
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(name='H1', fontName=HFont, fontSize=24, textColor=DARK_BLUE_COLOR, spaceAfter=14, leading=28))
    styles.add(ParagraphStyle(name='H2', fontName=HFont, fontSize=18, textColor=DARK_BLUE_COLOR, spaceAfter=10, spaceBefore=4, leading=16))
    styles.add(ParagraphStyle(name='H2_after_body', fontName='Helvetica-Bold', fontSize=18, textColor=DARK_BLUE_COLOR, spaceAfter=10, spaceBefore=12, leading=16))
    styles.add(ParagraphStyle(name='H3', fontName=HFont, fontSize=14, textColor=BLUE_ARCHIVE_COLOR, spaceAfter=8,))
    styles.add(ParagraphStyle(name='H4', fontName=HFont, fontSize=12, textColor=black, spaceAfter=6, spaceBefore=6))
    styles.add(ParagraphStyle(name='H5', fontName=HFont, fontSize=10, textColor=grey, spaceAfter=4, spaceBefore=4))
    styles.add(ParagraphStyle(name='Body', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=12))
    styles.add(ParagraphStyle(name='TableCell', parent=styles['Body'], spaceBefore=4))
    
    bullet_style = styles['Bullet']
    bullet_style.fontName = 'Helvetica'
    bullet_style.fontSize = 10
    bullet_style.leading = 14
    bullet_style.leftIndent = 20
    bullet_style.spaceAfter = 4

    def format_text(text):
        """
        Converts simple markdown (like **bold** and *italic*) into ReportLab rich text tags.
        """
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text) # Process bold first
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)   # Then process italic
        return text

    lines = md_content.split('\n')
    i = 0
    last_element_was_body = False # Flag to track the previous element type
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        is_table_separator = line.startswith('|--') or line.startswith('| :-')
        if line.startswith('|') and not is_table_separator and i + 1 < len(lines) and (lines[i+1].strip().startswith('|--') or lines[i+1].strip().startswith('| :-')):
            table_lines_raw = []
            j = i
            while j < len(lines) and lines[j].strip():
                table_lines_raw.append(lines[j])
                j += 1
            header_raw = table_lines_raw[0]
            body_lines = table_lines_raw[2:]
            rows_of_cells = []
            if body_lines:
                current_row_cells = [cell.strip() for cell in body_lines[0].split('|')[1:-1]]
                for k in range(1, len(body_lines)):
                    next_line = body_lines[k]
                    if next_line.strip().startswith('|'):
                        rows_of_cells.append(current_row_cells)
                        current_row_cells = [cell.strip() for cell in next_line.split('|')[1:-1]]
                    else:
                        if current_row_cells:
                            current_row_cells[-1] += " " + next_line.strip()
                rows_of_cells.append(current_row_cells)
            header = [h.strip() for h in header_raw.split('|')[1:-1]]
            data = [header]
            for row_cells in rows_of_cells:
                while len(row_cells) < len(header):
                    row_cells.append("")
                wrapped_row = [Paragraph(format_text(cell), styles['TableCell']) for cell in row_cells]
                data.append(wrapped_row)
            num_cols = len(header)
            col_width = doc_width / num_cols if num_cols > 0 else 0
            table = Table(data, colWidths=[col_width] * num_cols)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BLUE_ARCHIVE_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # This now works correctly
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), BACKGROUND_COLOR),
                ('GRID', (0, 0), (-1, -1), 1, grey),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.5 * cm))
            i = j
            last_element_was_body = False
            continue

        if line.startswith('## '):
            style_to_use = styles['H2_after_body'] if last_element_was_body else styles['H2']
            story.append(Paragraph(format_text(line[3:]), style_to_use))
            story.append(HorizontalRule(doc_width, color=BLUE_ARCHIVE_COLOR, thickness=4))
            story.append(Spacer(1, 0.4 * cm))
            last_element_was_body = False
        elif line.startswith('##### '):
            story.append(Paragraph(format_text(line[6:]), styles['H5']))
            last_element_was_body = False
        elif line.startswith('#### '):
            story.append(Paragraph(format_text(line[5:]), styles['H4']))
            last_element_was_body = False
        elif line.startswith('### '):
            story.append(Paragraph(format_text(line[4:]), styles['H3']))
            last_element_was_body = False
        elif line.startswith('# '):
            story.append(Paragraph(format_text(line[2:]), styles['H1']))
            last_element_was_body = False
        elif line.startswith('* '):
            story.append(Paragraph(f"•   {format_text(line[2:])}", styles['Bullet']))
            last_element_was_body = False
        elif line.startswith('---'):
            story.append(Spacer(1, 0.5 * cm))
            story.append(HorizontalRule(doc_width, color=BLUE_ARCHIVE_COLOR, thickness=0.5))
            story.append(Spacer(1, 0.5 * cm))
            last_element_was_body = False
        else:
            story.append(Paragraph(format_text(line), styles['Body']))
            last_element_was_body = True
        
        i += 1
            
    return story

if __name__ == "__main__":
    output_filename = f"Mission Brief {date.today()}.pdf"
    print("Process: Writing the PDF")
    
    try:
        with open('response.md', 'r', encoding='utf-8') as f:
            markdown_text = f.read()
    except FileNotFoundError:
        print("Error: 'response.md' not found. Please make sure the file is in the same directory.")
        exit()

    doc = SimpleDocTemplate(output_filename,
                          leftMargin=2*cm,
                          rightMargin=2*cm,
                          topMargin=3*cm,
                          bottomMargin=3*cm,
                          title="Sorasaki Hina",
                          author="Sorasaki Hina",
                          subject="Mission Brief")
    
    story_elements = parse_md_to_story(markdown_text, doc.width)
    
    doc.build(story_elements, 
              onFirstPage=create_mission_brief_template, 
              onLaterPages=create_mission_brief_template)
              
    print(f"Status: Successfully generated mission brief: {output_filename}")