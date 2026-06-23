from fpdf import FPDF
from datetime import datetime

class EvaluationPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 20)
        self.cell(0, 10, 'Nova AI Evaluation Report', border=False, ln=1, align='C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'Technical Interview Assessment', border=False, ln=1, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_evaluation_pdf(
    candidate_name: str,
    job_title: str,
    tech_score: int,
    comm_score: int,
    behavior_score: int,
    vision_score: int,
    overall_score: int,
    feedback: str,
    recommendation: str
) -> bytes:
    """Generates a PDF report summarizing the candidate's interview performance."""
    pdf = EvaluationPDF()
    pdf.add_page()

    # Candidate Info
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(50, 10, 'Candidate Name:', border=False)
    pdf.set_font('helvetica', '', 14)
    pdf.cell(0, 10, candidate_name, border=False, ln=1)
    
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(50, 10, 'Target Role:', border=False)
    pdf.set_font('helvetica', '', 14)
    pdf.cell(0, 10, job_title, border=False, ln=1)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(50, 10, 'Date:', border=False)
    pdf.set_font('helvetica', '', 14)
    pdf.cell(0, 10, datetime.now().strftime("%Y-%m-%d %H:%M"), border=False, ln=1)
    
    pdf.ln(10)

    # Scores
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Performance Scores', border='B', ln=1)
    pdf.ln(5)

    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(80, 10, 'Technical Score:', border=False)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'{tech_score} / 100', border=False, ln=1)

    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(80, 10, 'Communication Score:', border=False)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'{comm_score} / 100', border=False, ln=1)

    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(80, 10, 'Behavioral Score:', border=False)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'{behavior_score} / 100', border=False, ln=1)

    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(80, 10, 'Vision Score:', border=False)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'{vision_score} / 100', border=False, ln=1)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(80, 10, 'Overall Score:', border=False)
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, f'{overall_score} / 100', border=False, ln=1)
    
    pdf.ln(10)

    # Feedback
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Detailed Feedback', border='B', ln=1)
    pdf.ln(5)
    pdf.set_font('helvetica', '', 12)
    pdf.multi_cell(0, 8, feedback)

    pdf.ln(15)

    # Recommendation
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Final Recommendation', border='B', ln=1)
    pdf.ln(5)
    
    # Set color based on recommendation
    if recommendation.upper() == "HIRE":
        pdf.set_text_color(0, 150, 0)
    elif recommendation.upper() == "REJECT":
        pdf.set_text_color(200, 0, 0)
    else:
        pdf.set_text_color(200, 150, 0) # Hold/Orange
        
    pdf.set_font('helvetica', 'B', 18)
    pdf.cell(0, 10, recommendation.upper(), border=False, ln=1, align='C')

    # Return raw bytes
    return bytes(pdf.output())
