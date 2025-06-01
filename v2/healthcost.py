import gradio as gr
from gradio.interface import Interface
from gradio.components import Number, Dropdown, Textbox, Slider, Checkbox, File, JSON
import pandas as pd
import json
import os
from typing import List, Dict, Any, Optional, Union
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
import google.generativeai as genai
from google.generativeai import types
import time
from google.api_core import retry
import re

# Initialize Gemini with API key
GOOGLE_API_KEY = "AIzaSyAZz4wKgnwxhZ0W5NHTkLDa0BMxKb2KTuA"
genai.configure(api_key=GOOGLE_API_KEY)

def load_costs():
    """Load health costs by region and age group"""
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Default costs if file doesn't exist
    default_costs = [
        {'region': 'USA', 'age_group': '30-39', 'base_cost': 2000},
        {'region': 'USA', 'age_group': '40-49', 'base_cost': 3000},
        {'region': 'USA', 'age_group': '50-59', 'base_cost': 4000},
        {'region': 'USA', 'age_group': '60+', 'base_cost': 6000},
        {'region': 'Europe', 'age_group': '30-39', 'base_cost': 1500},
        {'region': 'Europe', 'age_group': '40-49', 'base_cost': 2250},
        {'region': 'Europe', 'age_group': '50-59', 'base_cost': 3000},
        {'region': 'Europe', 'age_group': '60+', 'base_cost': 4500},
        {'region': 'Asia', 'age_group': '30-39', 'base_cost': 1000},
        {'region': 'Asia', 'age_group': '40-49', 'base_cost': 1500},
        {'region': 'Asia', 'age_group': '50-59', 'base_cost': 2000},
        {'region': 'Asia', 'age_group': '60+', 'base_cost': 3000},
        {'region': 'Turkey', 'age_group': '30-39', 'base_cost': 800},
        {'region': 'Turkey', 'age_group': '40-49', 'base_cost': 1200},
        {'region': 'Turkey', 'age_group': '50-59', 'base_cost': 1600},
        {'region': 'Turkey', 'age_group': '60+', 'base_cost': 2400}
    ]
    
    # Try to load existing file, if not exists create with default data
    try:
        costs_df = pd.read_csv('data/health_costs_by_region.csv')
        if costs_df.empty:
            costs_df = pd.DataFrame(default_costs)
            costs_df.to_csv('data/health_costs_by_region.csv', index=False)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        costs_df = pd.DataFrame(default_costs)
        costs_df.to_csv('data/health_costs_by_region.csv', index=False)
    
    return costs_df

def load_weights():
    """Load chronic condition risk weights"""
    # Default weights if file doesn't exist
    default_weights = {
        "diabetes": 0.96,
        "hypertension": 0.72,
        "heart_disease": 1.20,
        "asthma": 0.33,
        "cancer": 1.44,
        "copd": 0.96,
        "depression": 0.48,
        "obesity": 0.72,
        "alzheimer": 1.20,
        "bone_cancer": 1.44
    }
    
    # Try to load existing file, if not exists create with default data
    try:
        with open('data/chronic_condition_weights.json', 'r') as f:
            weights = json.load(f)
            if not weights:
                weights = default_weights
                with open('data/chronic_condition_weights.json', 'w') as f:
                    json.dump(weights, f, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        weights = default_weights
        with open('data/chronic_condition_weights.json', 'w') as f:
            json.dump(weights, f, indent=4)
    
    return weights

class HealthCostPredictorAgent:
    def __init__(self, user_data):
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load required data
        self.cost_data = load_costs()
        self.weights = load_weights()
        
        # Define default data sources
        self.chronic_condition_sources = {
            "diabetes": "https://www.cdc.gov/diabetes/data/statistics-report/index.html",
            "hypertension": "https://www.heart.org/en/health-topics/high-blood-pressure",
            "heart_disease": "https://www.heart.org/en/health-topics/consumer-healthcare/what-is-cardiovascular-disease",
            "asthma": "https://www.lung.org/lung-health-diseases/lung-disease-lookup/asthma",
            "cancer": "https://www.cancer.org/cancer/cancer-basics/cancer-facts-and-figures.html",
            "copd": "https://www.lung.org/lung-health-diseases/lung-disease-lookup/copd",
            "depression": "https://www.nimh.nih.gov/health/statistics/major-depression",
            "obesity": "https://www.cdc.gov/obesity/data/index.html",
            "alzheimer": "https://www.alz.org/alzheimers-dementia/facts-figures",
            "bone_cancer": "https://www.cancer.org/cancer/bone-cancer.html"
        }
        
        self.family_history_risk = {
            "cancer": 0.15,
            "heart_disease": 0.20,
            "diabetes": 0.15,
            "alzheimer": 0.15,
            "bone_cancer": 0.15
        }
        
        self.lifestyle_source = "https://www.who.int/data/gho/data/themes/topics/health-behaviours"
        self.insurance_source = "https://www.oecd.org/health/health-data.htm"
        self.insurance_discount_rate = 0.3
        
        # Store user data
        if isinstance(user_data, str):
            try:
                self.user_data = json.loads(user_data)
            except json.JSONDecodeError:
                self.user_data = eval(user_data)
        else:
            self.user_data = user_data

    def handle_query(self):
        try:
            # Get prediction with details
            result = self.predict(self.user_data)
            
            # Generate recommendations
            recommendations = generate_recommendations(self.user_data, result['details'])
            
            # Generate report
            report = f"Predicted Annual Health Cost: ${result['final_cost']:,.2f}\n\n"
            report += "Calculation Steps:\n"
            for detail in result['details']:
                report += f"{detail['step']}: {detail['desc']} (Value: {detail['value']:.2f})\n"
            report += "\nRecommendations:\n"
            for rec in recommendations:
                report += f"- {rec}\n"
            
            # Save report to PDF
            pdf_path = self.save_report_to_pdf(result, recommendations)
            
            return report, pdf_path
        except Exception as e:
            print(f"Error in handle_query: {str(e)}")
            return f"Error generating report: {str(e)}", None

    def save_report_to_pdf(self, result: Dict[str, Any], recommendations: List[str]) -> str:
        """Save the report to a PDF file"""
        return generate_report(self.user_data)

    def _get_age_group(self, age: int) -> str:
        """Convert age to age group category."""
        if age < 40:
            return "30-39"
        elif age < 50:
            return "40-49"
        elif age < 60:
            return "50-59"
        else:
            return "60+"

    def _calculate_lifestyle_score(self, lifestyle_habits: str) -> int:
        """Calculate lifestyle score based on habits."""
        score = 0
        habits = lifestyle_habits.lower()
        
        # Exercise
        if "weekly" in habits and any(sport in habits for sport in ["basketball", "football", "tennis", "swimming", "running"]):
            score += 3
        elif "monthly" in habits and any(sport in habits for sport in ["basketball", "football", "tennis", "swimming", "running"]):
            score += 2
        elif "occasionally" in habits and any(sport in habits for sport in ["basketball", "football", "tennis", "swimming", "running"]):
            score += 1
            
        # Smoking and alcohol
        if "non-smoker" in habits:
            score += 2
        if "no alcohol" in habits:
            score += 2
            
        # Diet (assuming healthy if not specified)
        if "healthy diet" in habits or "balanced diet" in habits:
            score += 3
        else:
            score += 1  # Default score for unspecified diet
            
        return min(score, 10)

    def predict(self, input_data: Dict[str, Any]) -> dict:
        """
        Predict health costs based on input JSON data.
        """
        # Extract relevant data from input
        age = input_data.get('age', 0)
        region = input_data.get('location', 'USA')
        chronic_conditions = input_data.get('chronic_diseases', [])
        # Fix: if chronic_conditions is a string, handle properly
        if isinstance(chronic_conditions, str):
            if ',' in chronic_conditions:
                chronic_conditions = [c.strip() for c in chronic_conditions.split(',') if c.strip()]
            elif chronic_conditions.strip():
                chronic_conditions = [chronic_conditions.strip()]
            else:
                chronic_conditions = []
        elif not chronic_conditions:
            chronic_conditions = []
        # Only process valid, non-empty condition names
        chronic_conditions = [c for c in chronic_conditions if c and isinstance(c, str)]
        family_history = input_data.get('family_health_history', '').split(',')
        lifestyle_habits = input_data.get('lifestyle_habits', '')
        monthly_income = input_data.get('monthly_income', 0)
        
        # Calculate lifestyle score
        lifestyle_score = self._calculate_lifestyle_score(lifestyle_habits)
        
        # Determine insurance status based on income
        insurance_status = monthly_income >= 2000  # Assuming $2000 monthly income threshold for insurance
        
        # Get base cost for region and age group
        age_group = self._get_age_group(age)
        try:
            # Use proper pandas type hints
            cost_data: pd.DataFrame = self.cost_data
            filtered_data = cost_data.loc[(cost_data['region'] == region) & 
                                         (cost_data['age_group'] == age_group)]
            if not filtered_data.empty:
                base_cost = float(filtered_data['base_cost'].iloc[0])
            else:
                base_cost = float(cost_data['base_cost'].mean())
        except (IndexError, KeyError):
            base_cost = float(self.cost_data['base_cost'].mean())

        details = []
        details.append({
            'step': 'Base Cost',
            'desc': f'Region: {region}, Age Group: {age_group}',
            'value': base_cost,
            'source': self.insurance_source
        })

        # Calculate risk factors
        risk = 0.0
        chronic_risk = 0.0
        chronic_breakdown = []
        for condition in chronic_conditions:
            cond_info = self.weights.get(condition.lower(), {'value': 0.0, 'source': 'Data not available'})
            if isinstance(cond_info, dict):
                cond_risk = float(cond_info.get('value', 0.0))
                source = cond_info.get('source', 'Data not available')
            else:
                cond_risk = float(cond_info)
                source = 'Data not available'
            chronic_risk += cond_risk
            chronic_breakdown.append((condition, cond_risk, source))
        if chronic_breakdown:
            details.append({
                'step': 'Chronic Conditions',
                'desc': ', '.join([f"{c}: +{r:.2f} (Source: {s})" for c, r, s in chronic_breakdown]),
                'value': chronic_risk,
                'source': '; '.join([s for _, _, s in chronic_breakdown])
            })
        risk += chronic_risk

        family_risk = 0.0
        family_breakdown = []
        for condition in family_history:
            condition = condition.strip().lower()
            if condition in self.family_history_risk:
                fam_risk = self.family_history_risk[condition]
                family_risk += fam_risk
                family_breakdown.append((condition, fam_risk, self.chronic_condition_sources.get(condition, 'General medical research data')))
        if family_breakdown:
            details.append({
                'step': 'Family History',
                'desc': ', '.join([f"{c}: +{r:.2f} (Source: {s})" for c, r, s in family_breakdown]),
                'value': family_risk,
                'source': '; '.join([s for _, _, s in family_breakdown])
            })
        risk += family_risk

        lifestyle_risk = (10 - lifestyle_score) * 0.03
        details.append({
            'step': 'Lifestyle Score',
            'desc': f'Score: {lifestyle_score}/10 -> Risk: +{lifestyle_risk:.2f}',
            'value': lifestyle_risk,
            'source': self.lifestyle_source
        })
        risk += lifestyle_risk

        details.append({
            'step': 'Total Risk Factor',
            'desc': 'Sum of all risk factors (Chronic Conditions + Family History + Lifestyle)',
            'value': risk,
            'source': 'Internal Model Calculation'
        })

        predicted_cost = base_cost * (1 + risk)
        details.append({
            'step': 'Cost Before Insurance',
            'desc': f'Base Cost (${base_cost:,.2f}) x (1 + Total Risk {risk:.2f})',
            'value': predicted_cost,
            'source': 'Internal Model Calculation'
        })

        if insurance_status:
            discount_amount = predicted_cost * self.insurance_discount_rate
            final_cost = predicted_cost - discount_amount
            details.append({
                'step': 'Insurance Discount',
                'desc': f'Applied {self.insurance_discount_rate*100:.0f}% discount for insurance',
                'value': discount_amount,
                'source': self.insurance_source
            })
            details.append({
                'step': 'Final Cost After Insurance',
                'desc': 'Cost after insurance discount applied',
                'value': final_cost,
                'source': self.insurance_source
            })
        else:
            final_cost = predicted_cost
            details.append({
                'step': 'Insurance Discount',
                'desc': 'No insurance discount applied',
                'value': 0.0,
                'source': self.insurance_source
            })
            details.append({
                'step': 'Final Cost After Insurance',
                'desc': 'Cost after insurance discount applied',
                'value': final_cost,
                'source': self.insurance_source
            })

        return {
            'final_cost': round(final_cost, 2),
            'details': details,
            'lifestyle_score': lifestyle_score,
            'insurance_status': insurance_status
        }

def generate_report(user_json: Dict[str, Any]) -> str:
    """
    Generate a PDF report for health cost prediction.
    """
    # Extract user data from json
    age = user_json.get('age', 0)
    gender = user_json.get('gender', '')
    region = user_json.get('location', '')
    chronic_conditions = user_json.get('chronic_diseases', [])
    family_history = user_json.get('family_health_history', '').split(',')
    lifestyle_habits = user_json.get('lifestyle_habits', '')
    monthly_income = user_json.get('monthly_income', 0)
    
    # Initialize the predictor agent
    agent = HealthCostPredictorAgent(user_json)
    
    # Get prediction with details
    result = agent.predict(user_json)
    final_cost = result['final_cost']
    details = result['details']
    lifestyle_score = result['lifestyle_score']
    insurance_status = result['insurance_status']
    
    # Generate recommendations
    recommendations = generate_recommendations(user_json, details)
    
    # Create reports directory if it doesn't exist
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"health_cost_prediction_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # Create the PDF document
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
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
    
    source_style = ParagraphStyle(
        'SourceStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#7F8C8D'),  # Light gray
        spaceBefore=2,
        spaceAfter=6,
        fontName='Helvetica-Oblique'
    )
    
    # Build the content
    content = []
    
    # Title with logo or icon (if available)
    content.append(Paragraph("Health Cost Prediction Report", title_style))
    content.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", source_style))
    content.append(Spacer(1, 20))
    
    # Personal Information Section
    content.append(Paragraph("Personal Information", heading_style))
    content.append(Spacer(1, 10))
    
    personal_data = [
        ["Age:", str(age)],
        ["Gender:", gender],
        ["Region:", region],
        ["Lifestyle Score:", f"{lifestyle_score}/10"],
        ["Insurance Status:", "Yes" if insurance_status else "No"],
        ["Smoking:", "Yes" if "smoker" in lifestyle_habits.lower() else "No"],
        ["Alcohol Consumption:", "Yes" if "no alcohol" not in lifestyle_habits.lower() else "No"]
    ]
    
    personal_table = Table(personal_data, colWidths=[2*inch, 4*inch])
    personal_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),  # Lighter grid
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F8FA')),  # Light blue-gray
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#FFFFFF')),  # White
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),  # Dark gray text
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    content.append(personal_table)
    content.append(Spacer(1, 20))
    
    # Health Information Section
    content.append(Paragraph("Health Information", heading_style))
    content.append(Spacer(1, 10))
    
    health_data = [
        ["Chronic Conditions:", ", ".join(chronic_conditions) if chronic_conditions else "None reported"],
        ["Family History:", ", ".join(family_history) if family_history else "None reported"]
    ]
    
    health_table = Table(health_data, colWidths=[2*inch, 4*inch])
    health_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F8FA')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#FFFFFF')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    content.append(health_table)
    content.append(Spacer(1, 20))
    
    # Prediction Results Section with enhanced styling
    content.append(Paragraph("Prediction Results", heading_style))
    content.append(Spacer(1, 10))
    
    prediction_data = [
        ["Predicted Annual Health Cost:", f"${final_cost:,.2f}"]
    ]
    
    prediction_table = Table(prediction_data, colWidths=[2*inch, 4*inch])
    prediction_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F8FA')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#EBF5FB')),  # Light blue background for cost
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2874A6')),  # Blue for cost
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('FONTSIZE', (1, 0), (1, -1), 14),  # Larger font for cost
        ('PADDING', (0, 0), (-1, -1), 12),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Right align the cost
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    content.append(prediction_table)
    content.append(Spacer(1, 20))
    
    # Detailed Calculation Steps with enhanced styling
    if details:
        content.append(Paragraph("Cost Calculation Breakdown", heading_style))
        content.append(Spacer(1, 10))
        
        calc_data = [
            [
                Paragraph("Step", subheading_style),
                Paragraph("Description", subheading_style),
                Paragraph("Value", subheading_style),
                Paragraph("Source", source_style)
            ]
        ]
        
        for d in details:
            step_para = Paragraph(str(d.get('step', '')), normal_style)
            desc_para = Paragraph(str(d.get('desc', '')), normal_style)
            value_para = Paragraph(f"${d.get('value', 0):,.2f}", normal_style)
            source_para = Paragraph(d.get('source', ''), source_style)
            calc_data.append([step_para, desc_para, value_para, source_para])
        
        calc_table = Table(calc_data, colWidths=[1.0*inch, 2.5*inch, 1.0*inch, 3.3*inch], repeatRows=1)
        calc_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),  # Header background
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),  # Content background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#FFFFFF')),  # Header text color
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),  # Content text color
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),  # Content font
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # Header font size
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # Content font size
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right align values
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Alternating row colors
            *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FBFD')) for i in range(2, len(calc_data), 2)]
        ]))
        content.append(calc_table)
        content.append(Spacer(1, 20))
    
    # Recommendations Section with enhanced styling
    if recommendations:
        content.append(Paragraph("Personalized Recommendations", heading_style))
        content.append(Spacer(1, 10))
        
        for i, rec in enumerate(recommendations, 1):
            bullet_style = ParagraphStyle(
                'Bullet',
                parent=normal_style,
                leftIndent=20,
                firstLineIndent=-20,
                spaceBefore=4,
                spaceAfter=4
            )
            content.append(Paragraph(f"{i}. {rec}", bullet_style))
        content.append(Spacer(1, 20))
    
    # Disclaimer Section with enhanced styling
    content.append(Paragraph("Important Information", heading_style))
    content.append(Spacer(1, 10))
    
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
    
    disclaimer_text = """
    This report is generated using AI-powered analysis and should be reviewed by a qualified healthcare provider or financial advisor. 
    All calculations are based on provided data and industry-standard actuarial tables. The predictions and recommendations are for 
    informational purposes only and do not constitute medical or financial advice. Past performance is not indicative of future results.
    Please consult with appropriate professionals for personalized guidance.
    """
    
    content.append(Paragraph(disclaimer_text, disclaimer_style))
    content.append(Spacer(1, 20))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=source_style,
        alignment=1  # Center alignment
    )
    content.append(Paragraph(f"Report ID: {timestamp}", footer_style))
    
    # Build the PDF with enhanced styling
    doc.build(content)
    
    return filepath

def generate_recommendations(input_data: Dict[str, Any], calculation_details: List[Dict[str, Any]]) -> List[str]:
    """
    Generate personalized health and financial recommendations using Gemini,
    with accurate numerical references and no repetition.
    """
    
    prompt = f"""
You are a highly knowledgeable health and financial advisor.
Your task is to generate 15 **unique**, **user-specific**, and **data-driven** recommendations based on the following detailed user profile and risk assessment.
Each recommendation should:

- Refer **directly** to at least one user-specific input (e.g., "with 20000 USD debt", "based on your 1/10 lifestyle score", etc.)
- Be written as a **single, complete sentence**
- Include **exact numbers** from the input (e.g., "debt: 20000 USD", "monthly income: 4500 USD")
- Be **actionable**, **evidence-based**, and where applicable cite a source (e.g., WHO, CDC, NIH) in parentheses
- Avoid all forms of repetition or vague suggestions

Use the data below **as-is**. Do not round or interpret numbers. Use the original format (e.g., 20000 USD instead of "$20k" or "$20").

PATIENT PROFILE
- Name: {input_data.get('name_surname', 'N/A')}
- Age: {input_data.get('age', 'N/A')} years
- Gender: {input_data.get('gender', 'N/A')}
- Marital Status: {input_data.get('martial_status', 'N/A')}
- Education: {input_data.get('education_level', 'N/A')}
- Occupation: {input_data.get('occupation', 'N/A')}
- Location: {input_data.get('location', 'N/A')}
- Monthly Income: {input_data.get('monthly_income', 'N/A')} USD
- Monthly Expenses: {input_data.get('monthly_expenses', 'N/A')} USD
- Debt: {input_data.get('debt', 'N/A')} USD
- Assets: {input_data.get('assets', 'N/A')}

HEALTH PROFILE
- Chronic Conditions: {', '.join(input_data.get('chronic_diseases', []) or ['None reported'])}
- Family Medical History: {input_data.get('family_health_history', 'None reported')}
- Lifestyle Habits: {input_data.get('lifestyle_habits', 'N/A')}
- Lifestyle Score: {input_data.get('lifestyle_score', 'N/A')}/10

RETIREMENT GOALS
- Target Retirement Age: {input_data.get('target_retirement_age', 'N/A')}
- Target Retirement Income: {input_data.get('target_retirement_income', 'N/A')} USD/month

RISK CALCULATION SUMMARY
{chr(10).join([f"- {detail['step']}: {detail['desc']}" for detail in calculation_details])}

Please return exactly 15 recommendations in a numbered list (1–15), each on a new line, and strictly follow the above rules.
"""
    # Create Gemini model instance
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    response = model.generate_content(
        contents=prompt,
        generation_config=types.GenerationConfig(
            temperature=0.4,  # Lower temp = more deterministic & fact-based
            top_p=0.9,
            top_k=40
        )
    )
    text = response.text
    if not text:
        return ["Unable to generate recommendations at this time. Please consult with your healthcare provider."]
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    seen = set()
    unique_recommendations = []
    for line in lines:
        # Remove leading bullets, numbers, and whitespace
        clean = re.sub(r'^[•\-\d\.\s]+', '', line).strip()
        # Remove citation (parentheses and after)
        rec_main = re.split(r'\s*\([^)]*\)\s*$', clean)[0]
        # Normalize: lowercase, remove extra spaces, remove trailing dot
        norm = re.sub(r'\s+', ' ', rec_main).lower().rstrip('.')
        if norm and norm not in seen:
            unique_recommendations.append(clean)
            seen.add(norm)
        if len(unique_recommendations) == 15:
            break
    return unique_recommendations

def parse_custom_format(input_text: str) -> dict:
    """
    Parse the custom format into a proper JSON dictionary.
    Format:
    {
    key value,
    key value,
    ...
    }
    """
    try:
        # Remove curly braces and split by commas
        content = input_text.strip('{}').strip()
        lines = [line.strip() for line in content.split(',') if line.strip()]
        
        result = {}
        for line in lines:
            # Split by first space to separate key and value
            parts = line.split(' ', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                
                # Convert value to appropriate type
                if value.lower() == 'null':
                    value = None
                elif value.isdigit():
                    value = int(value)
                elif value.replace('.', '', 1).isdigit():
                    value = float(value)
                elif value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                
                result[key] = value
        
        return result
    except Exception as e:
        raise ValueError(f"Error parsing input format: {str(e)}")

def predict_health_cost(input_text: str) -> tuple[str, str | None]:
    """
    Predict health costs based on input and generate PDF report.
    """
    try:
        # Parse input text using custom parser
        input_data = parse_custom_format(input_text)
        
        # Initialize the predictor agent
        agent = HealthCostPredictorAgent(input_data)
        
        # Get prediction and report
        prediction_text, pdf_path = agent.handle_query()
        
        return prediction_text, pdf_path
    except ValueError as e:
        error_message = f"Invalid input format: {str(e)}"
        return error_message, None
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return error_message, None

# Define a function to handle the chatbot interaction

def chatbot_interface(input_text: str):
    prediction_text, pdf_path = predict_health_cost(input_text)
    return prediction_text, pdf_path

# Create a Gradio interface
demo = gr.Interface(
    fn=chatbot_interface,
    inputs=gr.Textbox(lines=20, label="Health Profile Input"),
    outputs=["text", gr.File(label="Download Report")],
    title="Health Cost Prediction Chatbot",
    description="Enter your health profile data to receive a cost prediction and download the report.",
)

# Comment out the Gradio launch to prevent it from running independently
# demo.launch()