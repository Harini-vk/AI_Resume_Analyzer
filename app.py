
from flask import Flask, render_template, request, send_file
import re
import fitz
import language_tool_python
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import uuid


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REPORT_FOLDER'] = 'reports'

# Create folders if not exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

# Sample Job Descriptions
job_descriptions = {
    'Software Engineer': "We are looking for a Software Engineer skilled in Python, Django, web development, and teamwork.",
    'Data Scientist': "Join our data team to build machine learning models, perform data analysis, and create visualizations.",
    'Frontend Developer': "Seeking a creative Frontend Developer skilled in HTML, CSS, JavaScript, React, and UI/UX design.",
    'Backend Developer': "Looking for a Backend Developer experienced with Flask, Node.js, SQL databases, and API integration.",
    'AI Engineer': "Hiring an AI Engineer to develop NLP models, recommendation systems, and AI-driven solutions."
}

# Updated Company + Position Specific Skills
company_skills = {
    'Google': {
        'Software Engineer': ['Python', 'Data Structures', 'System Design', 'Cloud Computing', 'Machine Learning'],
        'Data Scientist': ['Machine Learning', 'Statistics', 'Python', 'TensorFlow', 'BigQuery'],
    },
    'Microsoft': {
        'Software Engineer': ['Azure', 'C#', 'Cloud Computing', 'Problem Solving', 'System Design'],
        'Data Scientist': ['Azure ML', 'Data Analysis', 'Power BI', 'Python', 'Statistics'],
    },
    'Amazon': {
        'Software Engineer': ['AWS', 'Java', 'Leadership Principles', 'Data Structures', 'System Design'],
        'Data Scientist': ['AWS', 'Data Pipelines', 'Machine Learning', 'Python', 'Big Data'],
    }
}

# Helper Functions
def extract_skills(text):
    skills = re.findall(r'\b[A-Z][a-zA-Z]+\b', text)
    return list(set(skills))

import language_tool_python

# Connect to LanguageTool public server
# tool = language_tool_python.LanguageToolPublicAPI('en-US')
tool = language_tool_python.LanguageTool('en-US')

def check_grammar(text):
    matches = tool.check(text)
    return len(matches)

def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text

def create_pie_chart(skill_match_score, chart_filename):
    chart_dir = 'static/charts'
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, chart_filename)

    plt.figure(figsize=(6, 6))
    plt.pie([skill_match_score, 100 - skill_match_score], labels=["Matched", "Unmatched"], autopct='%1.1f%%', startangle=90, colors=['#28a745', '#dc3545'])
    plt.axis('equal')
    plt.savefig(chart_path)
    plt.close()
    return chart_path

def generate_pdf(summary, score, grammar_errors, skills, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Resume Analysis Report", ln=True, align="C")
    pdf.ln(10)

    pdf.multi_cell(0, 10, f"Summary:\n{summary}")
    pdf.ln(5)

    pdf.cell(0, 10, f"Skill Match Score: {score}%", ln=True)
    pdf.cell(0, 10, f"Grammar Errors: {grammar_errors}", ln=True)
    pdf.ln(5)

    pdf.cell(0, 10, "Matched Skills:", ln=True)
    for skill in skills:
        pdf.cell(0, 10, f"- {skill}", ln=True)

    report_path = os.path.join(app.config['REPORT_FOLDER'], filename)
    pdf.output(report_path)
    return report_path

# Main Route
@app.route('/', methods=['GET', 'POST'])
def index():
    companies = list(company_skills.keys())
    job_roles = list(job_descriptions.keys())

    if request.method == 'POST':
        file = request.files['resume']
        company_name = request.form['companyname']
        job_role = request.form['jobrole']
        job_description = request.form['jobdescription']

        if not file:
            return "No file uploaded."

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        resume_text = extract_text_from_pdf(filepath)

        if not job_description.strip():
            job_description = job_descriptions.get(job_role, "No description available for this role.")

        resume_skills = extract_skills(resume_text)
        jd_skills = extract_skills(job_description)
        matched_skills = list(set(resume_skills) & set(jd_skills))

        skill_match_score = round((len(matched_skills) / len(jd_skills)) * 100, 2) if jd_skills else 0
        grammar_errors = check_grammar(resume_text)

        # Company-position specific missing skills
        missing_company_skills = []
        if company_name and job_role:
            company_data = company_skills.get(company_name, {})
            required_skills = company_data.get(job_role, [])
            if required_skills:
                missing_company_skills = [skill for skill in required_skills if skill not in resume_skills]
            else:
                missing_company_skills = ["No data found for this company-position combination."]

        personalized_summary = f"Based on your resume and the selected {job_role} position at {company_name}, you have a skill match score of {skill_match_score}%. You demonstrate strengths in {', '.join(matched_skills)}. We recommend improving grammatical correctness, as {grammar_errors} issues were detected."

        chart_filename = f"{uuid.uuid4()}.png"
        chart_path = create_pie_chart(skill_match_score, chart_filename)

        pdf_filename = f"{uuid.uuid4()}.pdf"
        pdf_path = generate_pdf(personalized_summary, skill_match_score, grammar_errors, matched_skills, pdf_filename)

        return render_template('result.html', 
                               score=skill_match_score, 
                               errors=grammar_errors, 
                               skills=matched_skills, 
                               summary=personalized_summary, 
                               chart=f"charts/{chart_filename}",
                               report=pdf_filename,
                               companyname=company_name,
                               missing_company_skills=missing_company_skills)

    return render_template('index.html', companies=companies, job_roles=job_roles)

@app.route('/download/<report>')
def download(report):
    return send_file(os.path.join(app.config['REPORT_FOLDER'], report), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
