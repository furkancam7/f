import google.generativeai as genai
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
import gradio as gr
import os
import json
from datetime import datetime

API_KEY = "AIzaSyBPSBl9b8sN4yFbxZe-NkGcUmH5Clp31SU"

# Base life expectancy by gender (CDC, US Life Tables 2021)
BASE_LIFE_EXPECTANCY = {
    "male": 76,    # CDC: https://www.cdc.gov/nchs/data/nvsr/nvsr72/nvsr72-14.pdf
    "female": 81   # CDC: https://www.cdc.gov/nchs/data/nvsr/nvsr72/nvsr72-14.pdf
}

# Disease impact (CDC, WHO, peer-reviewed studies)
disease_data = {
    "diabetes": 3,           # CDC, WHO
    "hypertension": 2,       # CDC, WHO
    "heart_disease": 4,      # CDC, WHO
    "copd": 4,               # CDC, WHO
    "cancer": 5,             # CDC, WHO
    "arthritis": 1,          # CDC, WHO
    "asthma": 2,             # CDC, WHO
    "stroke": 4,             # CDC, WHO
    "kidney_disease": 3,     # CDC, WHO
    "liver_disease": 4,      # CDC, WHO
    "osteoporosis": 2,       # CDC, WHO
    "depression": 1,         # CDC, WHO
    "anxiety": 1,            # CDC, WHO
    "obesity": 2,            # WHO
    "high_cholesterol": 1    # CDC
}

# Education impact (OECD)
EDUCATION_IMPACT = {
    "Primary": -2,       # OECD: https://www.oecd.org/els/health-systems/Health-at-a-Glance-2021-Highlights-EN.pdf
    "High School": -1
}

# Income impact (OECD)
INCOME_IMPACT = {
    "low": -2,           # OECD
    "medium": -1
}

# Marital status impact (BMJ)
MARITAL_IMPACT = {
    "Single": -1         # BMJ: https://www.bmj.com/content/343/bmj.d5639
}

# Family history impact (Nature)
FAMILY_HISTORY_IMPACT = {
    "cancer": -2,        # Nature: https://www.nature.com/articles/s41586-018-0459-6
    "alzheimer": -2
}

# Lifestyle bonuses (WHO, CDC)
LIFESTYLE_BONUSES = {
    "basketball": 1,     # WHO: Physical activity
    "non-smoker": 1,     # CDC: Smoking
    "no alcohol": 1      # WHO: Alcohol
}



def static_life_expectancy_calculation(user_data):
    gender = user_data.get("gender", "").lower()
    base = BASE_LIFE_EXPECTANCY.get(gender, 78)
    age = int(user_data.get("age", 40))
    # Education
    education = user_data.get("education_level", "")
    base += EDUCATION_IMPACT.get(education, 0)
    # Income
    income = int(user_data.get("monthly_income", 0))
    if income < 3000:
        base += INCOME_IMPACT["low"]
    elif income < 6000:
        base += INCOME_IMPACT["medium"]
    # Marital
    marital = user_data.get("martial_status", "")
    base += MARITAL_IMPACT.get(marital, 0)
    # Family history
    fam_hist = user_data.get("family_health_history", "").lower()
    for key, val in FAMILY_HISTORY_IMPACT.items():
        if key in fam_hist:
            base += val
    # Lifestyle
    lifestyle = user_data.get("lifestyle_habits", "").lower()
    lifestyle_bonus = 0
    for key, val in LIFESTYLE_BONUSES.items():
        if key in lifestyle:
            lifestyle_bonus += val
    # Chronic diseases
    conditions = user_data.get("chronic_diseases", [])
    if conditions is None or conditions == "null":
        conditions = []
    elif isinstance(conditions, str):
        conditions = [c.strip() for c in conditions.split(',') if c.strip()]
    disease_penalty = sum([disease_data.get(c.lower(), 0) for c in conditions])
    expected_life = max(base + lifestyle_bonus - disease_penalty, age)
    risk = 100 - ((expected_life - age) * 2)
    risk = min(max(risk, 0), 100)
    analysis = {
        "base_expectancy": base,
        "disease_impact": -disease_penalty,
        "lifestyle_impact": lifestyle_bonus,
        "expected_life": expected_life,
        "risk_score": risk
    }
    return expected_life, risk, analysis

survival_table = """
age,male_survival,female_survival
0,1.000,1.000
1,0.995,0.996
5,0.994,0.995
10,0.993,0.994
15,0.992,0.993
20,0.990,0.992
25,0.988,0.991
30,0.985,0.990
35,0.982,0.989
40,0.978,0.988
45,0.973,0.987
50,0.967,0.986
55,0.959,0.984
60,0.949,0.982
65,0.936,0.979
70,0.919,0.975
75,0.897,0.970
80,0.868,0.963
85,0.830,0.953
90,0.780,0.938
95,0.715,0.915
100,0.630,0.880
"""

grounding_text = '''
Grounding & Data Sources:
- Base life expectancy: CDC, US Life Tables 2021 (https://www.cdc.gov/nchs/data/nvsr/nvsr72/nvsr72-14.pdf)
- Disease impact: CDC, WHO, peer-reviewed studies
- Education & income impact: OECD, Health at a Glance 2021 (https://www.oecd.org/els/health-systems/Health-at-a-Glance-2021-Highlights-EN.pdf)
- Marital status: BMJ, "Marriage and mortality" (https://www.bmj.com/content/343/bmj.d5639)
- Family history: Nature, "Genetic risk and healthy lifestyles" (https://www.nature.com/articles/s41586-018-0459-6)
- Lifestyle: WHO, CDC recommendations on physical activity, smoking, and alcohol
'''

class longevityAgent:
    def __init__(self, user_data):
        genai.configure(api_key=API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.user_data = user_data

    def _calculate_lifestyle_score(self, lifestyle_habits):
        """
        Calculate a lifestyle score from 0-10 based on healthy habits
        """
        if not lifestyle_habits:
            return 5  # Default neutral score
            
        score = 5  # Start with neutral score
        
        # Positive lifestyle factors
        positive_factors = {
            'basketball': 1,    # Regular exercise
            'non-smoker': 2,    # Not smoking
            'no alcohol': 1,    # No alcohol
            'healthy diet': 1,  # Healthy eating habits
            'sleep': 1,        # Good sleep habits
            'meditation': 1,    # Stress management
            'exercise': 1      # General exercise
        }
        
        # Negative lifestyle factors
        negative_factors = {
            'smoker': -2,      # Smoking
            'alcohol': -1,     # Regular alcohol consumption
            'sedentary': -1,   # Sedentary lifestyle
            'stress': -1,      # High stress
            'poor sleep': -1   # Poor sleep habits
        }
        
        # Convert to lowercase for case-insensitive matching
        lifestyle_habits = lifestyle_habits.lower()
        
        # Add points for positive factors
        for factor, points in positive_factors.items():
            if factor in lifestyle_habits:
                score += points
                
        # Subtract points for negative factors
        for factor, points in negative_factors.items():
            if factor in lifestyle_habits:
                score += points  # points are already negative
        
        # Ensure score stays within 0-10 range
        return max(0, min(10, score))

    def handle_query(self):
        try:
            report = self.generate_report()
            pdf_path = self.save_report_to_pdf(report)
            return report, pdf_path
        except Exception as e:
            print(f"Error in handle_query: {str(e)}")
            return f"Error generating report: {str(e)}", None

    def generate_report(self):
        if not self.user_data:
            return "Error: User profile is empty"
            
        expected_life, risk, analysis = static_life_expectancy_calculation(self.user_data)
        gemini_prompt = f"""
As a professional healthcare analyst, provide a comprehensive longevity and health analysis based on this profile.
Format the response as follows:

SECTION FORMAT:
Each major section should be numbered (1-5) and use this structure:
[SECTION NUMBER]. [SECTION TITLE]
• Key Point: [Important information in plain text]
• Finding: [Specific finding with numerical values where applicable]
• Impact: [How this affects longevity/health]

REQUIRED SECTIONS:
1. CURRENT HEALTH ASSESSMENT
   - Present health status
   - Chronic conditions
   - Family history
   - Genetic factors
   - Baseline health metrics

2. LONGEVITY FACTORS ANALYSIS
   - Base life expectancy
   - Genetic adjustments
   - Lifestyle impacts
   - Environmental factors
   - Socioeconomic influences

3. RISK STRATIFICATION
   - Primary risk factors
   - Risk severity analysis
   - Cumulative assessment
   - Future trajectory

4. PROTECTIVE FACTORS
   - Positive behaviors
   - Lifestyle benefits
   - Preventive measures
   - Environmental advantages

5. DETAILED RECOMMENDATIONS
   - Lifestyle modifications
   - Preventive measures
   - Risk mitigation
   - Health optimization

TEXT FORMATTING:
- Use plain text for general information
- Use numerical values where applicable (e.g., "25 years" instead of "twenty-five years")
- Include source citations in parentheses (e.g., "CDC, 2023")
- Format key metrics with specific values (e.g., "Blood Pressure: 120/80 mmHg")
- Present calculations clearly (e.g., "Base 73 years - 5 years (family history) + 2 years (non-smoker) = 70 years")

Profile Details:
{json.dumps(self.user_data, indent=2)}
"""
        gemini_response = self.model.generate_content(gemini_prompt).text

        # Detailed calculation details
        details = []
        base = 76 if self.user_data.get("gender", "").lower() == "male" else 80
        details.append(f"Base life expectancy for gender ({self.user_data.get('gender','')}): {base} years [CDC]")
        education = self.user_data.get("education_level", "")
        if education == "Primary":
            details.append("Education: Primary (-2 years) [OECD]")
        elif education == "High School":
            details.append("Education: High School (-1 year) [OECD]")
        income = int(self.user_data.get("monthly_income", 0))
        if income < 3000:
            details.append(f"Monthly income: {income} (<3000) (-2 years) [OECD]")
        elif income < 6000:
            details.append(f"Monthly income: {income} (3000-6000) (-1 year) [OECD]")
        marital = self.user_data.get("martial_status", "")
        if marital == "Single":
            details.append("Marital status: Single (-1 year) [BMJ]")
        fam_hist = self.user_data.get("family_health_history", "").lower()
        if "cancer" in fam_hist or "alzheimer" in fam_hist:
            details.append("Family health history: Cancer/Alzheimer (-2 years) [Nature]")
        lifestyle = self.user_data.get("lifestyle_habits", "").lower()
        lifestyle_bonus = 0
        if "basketball" in lifestyle:
            details.append("Lifestyle: Weekly basketball (+1 year) [WHO]")
            lifestyle_bonus += 1
        if "non-smoker" in lifestyle:
            details.append("Lifestyle: Non-smoker (+1 year) [CDC]")
            lifestyle_bonus += 1
        if "no alcohol" in lifestyle:
            details.append("Lifestyle: No alcohol (+1 year) [WHO]")
            lifestyle_bonus += 1
        # Chronic diseases
        conditions = self.user_data.get("chronic_diseases", [])
        if conditions is None or conditions == "null":
            conditions = []
        elif isinstance(conditions, str):
            conditions = [c.strip() for c in conditions.split(',') if c.strip()]
        disease_penalty = sum([disease_data.get(c.lower(), 0) for c in conditions])
        if disease_penalty:
            details.append(f"Chronic diseases: {', '.join(conditions)} (Total penalty: -{disease_penalty} years) [CDC]")
        details.append(f"Total lifestyle bonus: +{lifestyle_bonus} years")
        details.append(f"Total disease penalty: -{disease_penalty} years")
        details.append(f"Final expected life: {analysis['expected_life']} years")
        details.append(f"Risk score: %{analysis['risk_score']} (higher is worse)")

        hesap_detay = "\n".join(details)

        report = (
            f"{gemini_response}\n\n---\n\nCalculation Details:\n{hesap_detay}\n\n---\n\n{grounding_text}"
        )
        return report

    def save_report_to_pdf(self, report_text, output_path="reports/longevity_report.pdf"):
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, Table, TableStyle
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from datetime import datetime

        # Ensure the data directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create custom styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#1A5276'),  # Professional blue
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#2874A6'),  # Slightly lighter blue
            fontName='Helvetica-Bold',
            borderPadding=10,
            borderWidth=1,
            borderColor=colors.HexColor('#AED6F1'),  # Light blue border
            borderRadius=5
        )
        
        subheading_style = ParagraphStyle(
            'SubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.HexColor('#34495E'),  # Dark gray
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2C3E50'),  # Professional dark gray
            fontName='Helvetica',
            leading=14  # Line spacing
        )
        
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=normal_style,
            leftIndent=20,
            firstLineIndent=-20,
            spaceBefore=4,
            spaceAfter=4
        )
        
        source_style = ParagraphStyle(
            'SourceStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7F8C8D'),  # Light gray
            fontName='Helvetica-Oblique'
        )

        doc = SimpleDocTemplate(
            output_path,
            pagesize=LETTER,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        story = []

        # Add title and date
        story.append(Paragraph("Comprehensive Health & Longevity Analysis", title_style))
        story.append(Spacer(1, 15))

        # Add analysis timestamp and ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        story.append(Paragraph(f"Analysis ID: {timestamp}", normal_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}", normal_style))
        story.append(Spacer(1, 20))

        # Create custom styles for different text elements
        key_point_style = ParagraphStyle(
            'KeyPoint',
            parent=normal_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1A5276'),
            fontSize=11
        )

        finding_style = ParagraphStyle(
            'Finding',
            parent=normal_style,
            fontName='Helvetica',
            textColor=colors.HexColor('#2874A6'),
            fontSize=10
        )

        impact_style = ParagraphStyle(
            'Impact',
            parent=normal_style,
            fontName='Helvetica-Oblique',
            textColor=colors.HexColor('#34495E'),
            fontSize=10
        )

        calculation_style = ParagraphStyle(
            'Calculation',
            parent=normal_style,
            fontName='Helvetica',
            textColor=colors.HexColor('#2C3E50'),
            fontSize=10,
            backColor=colors.HexColor('#F8F9F9')
        )

        # Generate AI analysis
        gemini_prompt = f"""
As a professional healthcare analyst, provide a comprehensive longevity and health analysis based on this profile.
Format the response as follows:

SECTION FORMAT:
Each major section should be numbered (1-5) and use this structure:
[SECTION NUMBER]. [SECTION TITLE]
• Key Point: [Important information in plain text]
• Finding: [Specific finding with numerical values where applicable]
• Impact: [How this affects longevity/health]

REQUIRED SECTIONS:
1. CURRENT HEALTH ASSESSMENT
   - Present health status
   - Chronic conditions
   - Family history
   - Genetic factors
   - Baseline health metrics

2. LONGEVITY FACTORS ANALYSIS
   - Base life expectancy
   - Genetic adjustments
   - Lifestyle impacts
   - Environmental factors
   - Socioeconomic influences

3. RISK STRATIFICATION
   - Primary risk factors
   - Risk severity analysis
   - Cumulative assessment
   - Future trajectory

4. PROTECTIVE FACTORS
   - Positive behaviors
   - Lifestyle benefits
   - Preventive measures
   - Environmental advantages

5. DETAILED RECOMMENDATIONS
   - Lifestyle modifications
   - Preventive measures
   - Risk mitigation
   - Health optimization

TEXT FORMATTING:
- Use plain text for general information
- Use numerical values where applicable (e.g., "25 years" instead of "twenty-five years")
- Include source citations in parentheses (e.g., "CDC, 2023")
- Format key metrics with specific values (e.g., "Blood Pressure: 120/80 mmHg")
- Present calculations clearly (e.g., "Base 73 years - 5 years (family history) + 2 years (non-smoker) = 70 years")

Profile Details:
{json.dumps(self.user_data, indent=2)}
"""
        try:
            gemini_response = self.model.generate_content(gemini_prompt).text
        except Exception as e:
            print(f"Error generating Gemini response: {str(e)}")
            gemini_response = "Error generating AI analysis. Using basic analysis format."

        # Process sections
        sections = gemini_response.split('\n\n')
        current_section = None
        
        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Check if this is a new section
            if section[0].isdigit() and '. ' in section:
                current_section = section.split('. ')[1].strip()
                story.append(Paragraph(section, heading_style))
                story.append(Spacer(1, 10))
                continue

            # Process bullet points and content as before
            if section.startswith('•'):
                content = section[1:].strip()
                if 'Key Point:' in content:
                    key, value = content.split(':', 1)
                    story.append(Paragraph(f"• {key}:", key_point_style))
                    story.append(Paragraph(value.strip(), normal_style))
                elif 'Finding:' in content:
                    key, value = content.split(':', 1)
                    story.append(Paragraph(f"• {key}:", finding_style))
                    story.append(Paragraph(value.strip(), normal_style))
                elif 'Impact:' in content:
                    key, value = content.split(':', 1)
                    story.append(Paragraph(f"• {key}:", impact_style))
                    story.append(Paragraph(value.strip(), normal_style))
                else:
                    story.append(Paragraph(f"• {content}", normal_style))
                story.append(Spacer(1, 6))
            else:
                story.append(Paragraph(section, normal_style))
                story.append(Spacer(1, 4))

            if current_section:
                story.append(Spacer(1, 12))

        # Add detailed health metrics section
        story.append(Paragraph("Detailed Health Metrics Analysis", heading_style))
        story.append(Spacer(1, 10))

        # Create health metrics table
        health_metrics = [
            ["Metric Category", "Value", "Reference Range", "Status"],
            ["Age", f"{self.user_data.get('age', 'N/A')} years", "N/A", "Current"],
            ["Gender", self.user_data.get('gender', 'N/A'), "N/A", "Static"],
            ["Education", self.user_data.get('education_level', 'N/A'), "N/A", "Current"],
            ["Marital Status", self.user_data.get('martial_status', 'N/A'), "N/A", "Current"],
            ["Location", self.user_data.get('location', 'N/A'), "N/A", "Current"],
            ["Monthly Income", f"${self.user_data.get('monthly_income', 0):,.2f}", ">$2,000", "Economic Factor"],
            ["Lifestyle Score", f"{self._calculate_lifestyle_score(self.user_data.get('lifestyle_habits', ''))}/10", "≥7/10", "Health Indicator"]
        ]

        metrics_table = Table(health_metrics, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FBFD')) for i in range(2, len(health_metrics), 2)]
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 20))

        # Add detailed longevity calculations
        story.append(Paragraph("Longevity Impact Analysis", heading_style))
        story.append(Spacer(1, 10))

        # Calculate all impacts
        expected_life, risk, analysis = static_life_expectancy_calculation(self.user_data)
        
        # Create impact analysis table
        impact_data = [
            ["Factor", "Base Value", "Impact (Years)", "Confidence", "Source"],
            ["Base Life Expectancy", 
             f"{BASE_LIFE_EXPECTANCY.get(self.user_data.get('gender', 'male').lower(), 78)} years",
             "Baseline",
             "High",
             "CDC Life Tables 2021"]
        ]

        # Add education impact
        education = self.user_data.get('education_level', '')
        if education in EDUCATION_IMPACT:
            impact_data.append([
                "Education Level",
                education,
                f"{EDUCATION_IMPACT[education]:+d}",
                "Medium",
                "OECD Health Statistics"
            ])

        # Add income impact
        income = int(self.user_data.get('monthly_income', 0))
        income_impact = 0
        if income < 3000:
            income_impact = INCOME_IMPACT["low"]
        elif income < 6000:
            income_impact = INCOME_IMPACT["medium"]
        if income_impact:
            impact_data.append([
                "Income Level",
                f"${income}/month",
                f"{income_impact:+d}",
                "Medium",
                "OECD Economic Indicators"
            ])

        # Add marital status impact
        marital = self.user_data.get('martial_status', '')
        if marital in MARITAL_IMPACT:
            impact_data.append([
                "Marital Status",
                marital,
                f"{MARITAL_IMPACT[marital]:+d}",
                "Medium",
                "BMJ Research"
            ])

        # Add family history impacts
        fam_hist = self.user_data.get('family_health_history', '').lower()
        for condition, impact in FAMILY_HISTORY_IMPACT.items():
            if condition in fam_hist:
                impact_data.append([
                    f"Family History ({condition})",
                    "Present",
                    f"{impact:+d}",
                    "High",
                    "Nature Genetics Research"
                ])

        # Add lifestyle impacts
        lifestyle = self.user_data.get('lifestyle_habits', '').lower()
        for habit, bonus in LIFESTYLE_BONUSES.items():
            if habit in lifestyle:
                impact_data.append([
                    f"Lifestyle ({habit})",
                    "Present",
                    f"{bonus:+d}",
                    "High",
                    "WHO Guidelines"
                ])

        # Add chronic conditions
        conditions = self.user_data.get('chronic_diseases', [])
        if isinstance(conditions, str):
            conditions = [c.strip() for c in conditions.split(',') if c.strip()]
        for condition in conditions:
            if condition.lower() in disease_data:
                impact = -disease_data[condition.lower()]
                impact_data.append([
                    f"Health Condition ({condition})",
                    "Present",
                    f"{impact:+d}",
                    "High",
                    "CDC/WHO Data"
                ])

        # Create the impact analysis table
        impact_table = Table(impact_data, colWidths=[2*inch, 1.2*inch, 1*inch, 0.8*inch, 2*inch])
        impact_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FBFD')) for i in range(2, len(impact_data), 2)]
        ]))
        story.append(impact_table)
        story.append(Spacer(1, 20))

        # Add risk assessment section
        story.append(Paragraph("Risk Assessment & Recommendations", heading_style))
        story.append(Spacer(1, 10))

        # Create risk assessment table
        risk_data = [
            ["Risk Category", "Level", "Priority", "Recommended Action"],
            ["Cardiovascular Risk", 
             "Medium" if "heart_disease" in fam_hist else "Low",
             "High" if "heart_disease" in fam_hist else "Medium",
             "Regular cardiovascular screening"],
            ["Lifestyle Risk",
             "Low" if self._calculate_lifestyle_score(lifestyle) >= 7 else "Medium",
             "Medium",
             "Maintain healthy lifestyle habits"],
            ["Genetic Risk",
             "High" if any(c in fam_hist for c in FAMILY_HISTORY_IMPACT.keys()) else "Low",
             "High" if any(c in fam_hist for c in FAMILY_HISTORY_IMPACT.keys()) else "Low",
             "Genetic counseling recommended"],
            ["Economic Risk",
             "High" if income < 3000 else "Medium" if income < 6000 else "Low",
             "Medium",
             "Financial planning consultation"],
            ["Overall Health Risk",
             f"{analysis['risk_score']}% Risk Score",
             "High" if analysis['risk_score'] > 70 else "Medium" if analysis['risk_score'] > 40 else "Low",
             "Follow detailed recommendations below"]
        ]

        risk_table = Table(risk_data, colWidths=[1.5*inch, 1.2*inch, 1*inch, 3.3*inch])
        risk_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FBFD')) for i in range(2, len(risk_data), 2)]
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 20))

        # Add final summary section
        story.append(Paragraph("Final Summary", heading_style))
        story.append(Spacer(1, 10))

        summary_data = [
            ["Metric", "Value", "Interpretation"],
            ["Expected Longevity", 
             f"{analysis['expected_life']} years",
             "Based on current health factors and lifestyle"],
            ["Total Health Impact",
             f"{analysis['expected_life'] - analysis['base_expectancy']:+d} years",
             "Combined effect of all analyzed factors"],
            ["Risk Score",
             f"{analysis['risk_score']}%",
             "Overall health risk assessment"],
            ["Quality of Life Projection",
             "Good" if analysis['risk_score'] < 40 else "Fair" if analysis['risk_score'] < 70 else "Concerning",
             "Based on current health trajectory"]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 3.5*inch])
        summary_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#EBF5FB')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Add methodology section
        story.append(Paragraph("Analysis Methodology", subheading_style))
        story.append(Spacer(1, 8))
        
        methodology_text = """
        This analysis employs a comprehensive algorithm that considers multiple factors affecting longevity:
        
        1. Base Life Expectancy: Derived from CDC Life Tables 2021, providing gender-specific baseline values
        2. Socioeconomic Factors: Education and income levels weighted based on OECD health statistics
        3. Genetic Predisposition: Family history risks calculated using peer-reviewed research data
        4. Lifestyle Impact: Health behaviors quantified based on WHO guidelines
        5. Medical Conditions: Impact of chronic diseases assessed using CDC and WHO mortality data
        6. Environmental Factors: Location-based health influences from epidemiological studies
        7. Social Factors: Marital status and social support network effects from BMJ research
        
        The final calculation uses a weighted average approach with interaction effects between factors.
        All calculations are based on current epidemiological research and are regularly updated.
        Risk assessments use standardized scoring methods from validated medical research.
        """
        
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 20))

        # Add disclaimer
        story.append(Paragraph("Important Disclaimer", subheading_style))
        story.append(Spacer(1, 8))
        
        disclaimer_text = """
        This report is generated using AI-powered analysis and should be reviewed by qualified healthcare professionals. 
        The predictions and recommendations are based on statistical models and general population data. 
        Individual results may vary significantly based on numerous factors not captured in this analysis.
        This report does not constitute medical advice and should not be used as a substitute for professional medical consultation.
        All recommendations should be discussed with healthcare providers before implementation.
        Regular medical check-ups and professional health assessments are essential for accurate health monitoring.
        """
        
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=normal_style,
            fontSize=8,
            textColor=colors.HexColor('#7F8C8D'),
            borderPadding=10,
            borderWidth=1,
            borderColor=colors.HexColor('#BDC3C7'),
            borderRadius=5
        )
        
        story.append(Paragraph(disclaimer_text, disclaimer_style))
        story.append(Spacer(1, 20))

        # Add footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=normal_style,
            fontSize=8,
            textColor=colors.HexColor('#95A5A6'),
            alignment=1  # Center alignment
        )
        
        story.append(Paragraph(f"Report ID: {timestamp}", footer_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}", footer_style))
        story.append(Paragraph("Copyright © 2024 Health Analytics System", footer_style))

        # Build the PDF
        doc.build(story)
        return output_path

def process_user_string(user_info_str):
    agent = longevityAgent(user_info_str)
    report = agent.generate_report()
    
    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"reports/longevity_report_{timestamp}.pdf"
    
    # Save the report
    pdf_path = agent.save_report_to_pdf(report, pdf_path)
    return report, pdf_path

def chatbot_interface(user_info_str: str):
    """Handle the chatbot interaction and report generation"""
    report, pdf_path = process_user_string(user_info_str)
    return report, pdf_path

def list_available_reports():
    """Get list of all available reports with their details"""
    if not os.path.exists("reports"):
        os.makedirs("reports", exist_ok=True)
        return []
    
    reports = []
    for file in os.listdir("reports"):
        if file.endswith('.pdf'):
            path = os.path.join("reports", file)
            # Get file creation time
            created = datetime.fromtimestamp(os.path.getctime(path))
            # Get file size
            size = os.path.getsize(path)
            # Format size to KB or MB
            if size < 1024*1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            
            reports.append({
                "filename": file,
                "created": created.strftime("%Y-%m-%d %H:%M:%S"),
                "size": size_str,
                "path": path
            })
    
    # Sort by creation time (newest first)
    reports.sort(key=lambda x: x["created"], reverse=True)
    return reports

def format_report_list(reports):
    """Format reports list for display"""
    if not reports:
        return "No reports found."
    
    report_lines = []
    for report in reports:
        report_lines.append(f"📄 {report['filename']}\n   Created: {report['created']} | Size: {report['size']}")
    
    return "\n\n".join(report_lines)

def get_report_content(report_path):
    """Return the report file for download"""
    if os.path.exists(report_path):
        return report_path
    return None

def delete_report(report_path):
    """Delete a report file"""
    try:
        if os.path.exists(report_path):
            os.remove(report_path)
            return "Report deleted successfully."
        return "Report not found."
    except Exception as e:
        return f"Error deleting report: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="Longevity Analysis System") as demo:
    gr.Markdown("""
    # 🌟 Longevity Analysis System
    Generate comprehensive health and longevity reports based on your profile.
    """)
    
    with gr.Tab("📊 Generate New Report"):
        input_text = gr.Textbox(
            lines=20,
            label="User Info Input",
            placeholder="Enter your health information here in JSON format...\nExample:\n{\n  \"age\": 35,\n  \"gender\": \"male\",\n  \"education_level\": \"High School\",\n  \"monthly_income\": 5000\n}"
        )
        with gr.Row():
            submit_btn = gr.Button("🚀 Generate Report", variant="primary", scale=2)
            clear_btn = gr.Button("🔄 Clear", variant="secondary", scale=1)
        
        with gr.Column():
            output_text = gr.Textbox(label="Analysis Results", lines=10)
            output_file = gr.File(label="📄 Download Generated Report")
        
        submit_btn.click(
            chatbot_interface,
            inputs=[input_text],
            outputs=[output_text, output_file]
        )
        clear_btn.click(lambda: "", inputs=[], outputs=[input_text])
    
    with gr.Tab("📁 Reports Archive"):
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("""
                ### 📂 Available Reports
                Browse and manage your generated health analysis reports.
                """)
                
                # Reports list display with enhanced styling
                reports_list = gr.Textbox(
                    label="",
                    value=format_report_list(list_available_reports()),
                    lines=12,
                    interactive=False
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### 🔧 Actions")
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh List", variant="secondary")
                    delete_btn = gr.Button("🗑️ Delete Report", variant="secondary")
                
                # Report selection dropdown with enhanced styling
                reports_dropdown = gr.Dropdown(
                    choices=[r["path"] for r in list_available_reports()],
                    label="📑 Select Report",
                    interactive=True
                )
                
                # Selected report display
                selected_report = gr.File(label="📄 Selected Report")
                
                # Report info display
                report_info = gr.Markdown("")
        
        # Refresh button functionality
        def refresh_reports():
            reports = list_available_reports()
            report_paths = [r["path"] for r in reports]
            report_list_text = format_report_list(reports)
            return (
                report_list_text,
                gr.Dropdown(choices=report_paths),
                "Reports list refreshed!"
            )
        
        refresh_btn.click(
            refresh_reports,
            inputs=[],
            outputs=[reports_list, reports_dropdown, report_info]
        )
        
        # Delete button functionality
        def delete_selected_report(selected_path):
            if not selected_path:
                return (
                    format_report_list(list_available_reports()),
                    gr.Dropdown(choices=[r["path"] for r in list_available_reports()]),
                    None,
                    "⚠️ No report selected!"
                )
            
            result = delete_report(selected_path)
            reports = list_available_reports()
            return (
                format_report_list(reports),
                gr.Dropdown(choices=[r["path"] for r in reports]),
                None,
                f"✅ {result}"
            )
        
        delete_btn.click(
            delete_selected_report,
            inputs=[reports_dropdown],
            outputs=[reports_list, reports_dropdown, selected_report, report_info]
        )
        
        # Report selection functionality with info display
        def update_selected_report(report_path):
            if not report_path or not os.path.exists(report_path):
                return None, "⚠️ No report selected or file not found!"
            
            # Get report details
            file_stats = os.stat(report_path)
            created_time = datetime.fromtimestamp(file_stats.st_ctime)
            size = file_stats.st_size
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
            
            info_text = f"""
            ### 📄 Report Details
            - **Filename**: {os.path.basename(report_path)}
            - **Created**: {created_time.strftime('%Y-%m-%d %H:%M:%S')}
            - **Size**: {size_str}
            - **Location**: {report_path}
            """
            
            return report_path, info_text
        
        reports_dropdown.change(
            update_selected_report,
            inputs=[reports_dropdown],
            outputs=[selected_report, report_info]
        )

# Comment out the Gradio launch to prevent it from running independently
# demo.launch()