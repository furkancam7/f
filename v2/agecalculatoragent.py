import gradio as gr
import os
import json
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import google.generativeai as genai
import re
from google.generativeai import types

# Initialize Gemini API key
GEMINI_API_KEY = "AIzaSyCH9Nad-vGnVt55-YJ0-QXMvkmPWDwDJaQ"
genai.configure(api_key=GEMINI_API_KEY)

@dataclass
class UserProfile:
    name_surname: str
    age: int
    email: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    number_of_children: Optional[int] = 0
    education_level: Optional[str] = None
    occupation: Optional[str] = None
    annual_working_hours: Optional[int] = 2080  # Default 40 hours/week * 52 weeks
    monthly_income: Optional[float] = 0.0
    monthly_expenses: Optional[float] = 0.0
    debt: Optional[float] = 0.0
    assets: Optional[str] = None
    location: Optional[str] = None
    chronic_diseases: Optional[Union[str, List[str]]] = None
    lifestyle_habits: Optional[str] = None
    family_health_history: Optional[str] = None
    target_retirement_age: Optional[int] = 65
    target_retirement_income: Optional[float] = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create UserProfile from dictionary data"""
        # Handle chronic diseases list/string conversion
        chronic_diseases = data.get('chronic_diseases', None)
        if isinstance(chronic_diseases, str):
            if chronic_diseases.strip():
                if ',' in chronic_diseases:
                    chronic_diseases = [c.strip() for c in chronic_diseases.split(',')]
                else:
                    chronic_diseases = [chronic_diseases.strip()]
            else:
                chronic_diseases = []

        # Convert string values to appropriate types
        profile_data = {
            'name_surname': str(data.get('name_surname', '')),
            'age': int(data.get('age', 0)),
            'email': str(data.get('email', '')),
            'gender': str(data.get('gender', '')),
            'marital_status': str(data.get('marital_status', '')),
            'number_of_children': int(data.get('number_of_children', 0)),
            'education_level': str(data.get('education_level', '')),
            'occupation': str(data.get('occupation', '')),
            'annual_working_hours': int(data.get('annual_working_hours', 2080)),
            'monthly_income': float(data.get('monthly_income', 0.0)),
            'monthly_expenses': float(data.get('monthly_expenses', 0.0)),
            'debt': float(data.get('debt', 0.0)),
            'assets': str(data.get('assets', '')),
            'location': str(data.get('location', '')),
            'chronic_diseases': chronic_diseases,
            'lifestyle_habits': str(data.get('lifestyle_habits', '')),
            'family_health_history': str(data.get('family_health_history', '')),
            'target_retirement_age': int(data.get('target_retirement_age', 65)),
            'target_retirement_income': float(data.get('target_retirement_income', 0.0))
        }
        return cls(**profile_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert UserProfile to dictionary"""
        return {
            'name_surname': self.name_surname,
            'age': self.age,
            'email': self.email,
            'gender': self.gender,
            'marital_status': self.marital_status,
            'number_of_children': self.number_of_children,
            'education_level': self.education_level,
            'occupation': self.occupation,
            'annual_working_hours': self.annual_working_hours,
            'monthly_income': self.monthly_income,
            'monthly_expenses': self.monthly_expenses,
            'debt': self.debt,
            'assets': self.assets,
            'location': self.location,
            'chronic_diseases': self.chronic_diseases,
            'lifestyle_habits': self.lifestyle_habits,
            'family_health_history': self.family_health_history,
            'target_retirement_age': self.target_retirement_age,
            'target_retirement_income': self.target_retirement_income
        }

class RetirementCalculator:
    def __init__(self, user_data=None):
        # Base life expectancy by gender
        self.base_life_expectancy = {
            "male": 76,
            "female": 81
        }
        
        # Health impact factors
        self.health_impact_factors = {
            "alzheimer's": -5,
            "cancer": -7,
            "diabetes": -5,
            "heart_disease": -7,
            "hypertension": -3
        }
        
        # Parse user data if provided
        if isinstance(user_data, str):
            try:
                self.user_data = json.loads(user_data)
            except json.JSONDecodeError:
                self.user_data = self.parse_custom_format(user_data)
        else:
            self.user_data = user_data

    def parse_custom_format(self, input_text: str) -> dict:
        """Parse the custom format into a proper dictionary"""
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
                    if not value:
                        value = None
                    elif isinstance(value, str):
                        # Only process string values
                        str_value = str(value).lower()
                        if str_value == 'null':
                            value = None
                        elif value.isdigit():
                            value = int(value)
                        elif value.replace('.', '', 1).isdigit():
                            value = float(value)
                        elif str_value in ['true', 'false']:
                            value = str_value == 'true'
                    
                    result[key] = value
            
            return result
        except Exception as e:
            raise ValueError(f"Error parsing input format: {str(e)}")

    def handle_query(self):
        """Handle the query and generate report"""
        try:
            if not self.user_data:
                return "Error: User profile is empty", None
            
            # Create UserProfile object from user_data
            profile = UserProfile.from_dict(self.user_data)
            
            results = self.recommend_retirement_age(profile)
            output, output_path = create_retirement_profile(self.format_user_data(profile))
            return output, output_path
        except Exception as e:
            print(f"Error in handle_query: {str(e)}")
            return f"Error generating report: {str(e)}", None

    def format_user_data(self, profile):
        """Format user data for the create_retirement_profile function"""
        return f"""
        {{
        name_surname {profile.name_surname},
        age {profile.age},
        email {profile.email},
        gender {profile.gender},
        marital_status {profile.marital_status},
        number_of_children {profile.number_of_children},
        education_level {profile.education_level},
        occupation {profile.occupation},
        anual_working_hours {profile.annual_working_hours},
        monthly_income {profile.monthly_income},
        monthly_expenses {profile.monthly_expenses},
        debt {profile.debt},
        assets {profile.assets},
        location {profile.location},
        chronic_diseases {profile.chronic_diseases},
        lifestyle_habits {profile.lifestyle_habits},
        family_health_history {profile.family_health_history},
        target_retirement_age {profile.target_retirement_age},
        target_retirement_income {profile.target_retirement_income}
        }}
        """

    def calculate_life_expectancy(self, profile: UserProfile) -> float:
        """Calculate estimated life expectancy based on user profile."""
        gender = str(profile.gender or '').lower()
        base_expectancy = self.base_life_expectancy.get(gender, 78)
        
        # Adjust for family health history
        health_adjustment = 0
        if profile.family_health_history:
            family_history = str(profile.family_health_history).lower()
            for condition in self.health_impact_factors:
                if condition.lower() in family_history:
                    health_adjustment += self.health_impact_factors[condition]
        
        # Adjust for lifestyle habits
        lifestyle_adjustment = 0
        if profile.lifestyle_habits:
            lifestyle = str(profile.lifestyle_habits).lower()
            if "non-smoker" in lifestyle:
                lifestyle_adjustment += 5
            if "weekly" in lifestyle:
                lifestyle_adjustment += 3
        
        return max(60, base_expectancy + health_adjustment + lifestyle_adjustment)

    def calculate_financial_readiness(self, profile: UserProfile) -> Tuple[float, Dict[str, float]]:
        """Calculate financial readiness for retirement."""
        # Calculate annual savings
        monthly_income = profile.monthly_income or 0.0
        monthly_expenses = profile.monthly_expenses or 0.0
        annual_savings = (monthly_income - monthly_expenses) * 12
        
        # Calculate years until target retirement
        target_retirement_age = profile.target_retirement_age or 65
        years_to_retirement = max(target_retirement_age - (profile.age or 0), 1)
        
        # Calculate future value of current assets
        # Assuming 7% annual return on investments
        future_assets = 0.0
        if profile.assets and "savings" in profile.assets.lower():
            try:
                savings = float(profile.assets.split("$")[1].split()[0].replace(",", ""))
                future_assets += savings * (1.07) ** years_to_retirement
            except (IndexError, ValueError):
                future_assets = 0.0
        
        # Calculate future value of annual savings
        future_annual_savings = annual_savings * ((1.07) ** years_to_retirement - 1) / 0.07
        
        total_retirement_savings = future_assets + future_annual_savings
        
        # Calculate retirement duration
        retirement_duration = max(self.calculate_life_expectancy(profile) - (target_retirement_age or 65), 1)
        
        # Calculate required savings for target retirement income
        target_retirement_income = profile.target_retirement_income or 0.0
        required_savings = target_retirement_income * 12 * retirement_duration
        required_savings = max(required_savings, 1.0)
        
        financial_metrics = {
            "total_retirement_savings": total_retirement_savings,
            "required_savings": required_savings,
            "annual_retirement_expenses": target_retirement_income * 12,
            "retirement_duration": retirement_duration
        }
        
        return total_retirement_savings / required_savings, financial_metrics

    def recommend_retirement_age(self, profile: UserProfile) -> dict:
        """Calculate recommended retirement age based on various factors."""
        # Calculate life expectancy
        life_expectancy = self.calculate_life_expectancy(profile)
        
        # Calculate financial readiness
        financial_ratio, financial_metrics = self.calculate_financial_readiness(profile)
        
        # Determine if target retirement age is feasible
        if financial_ratio >= 1.2:
            scenario = "early_retirement"
        elif financial_ratio >= 0.8:
            scenario = "standard_retirement"
        else:
            scenario = "delayed_retirement"
        
        return {
            "recommended_retirement_age": profile.target_retirement_age,
            "life_expectancy": life_expectancy,
            "financial_ratio": financial_ratio,
            "scenario": scenario,
            "financial_metrics": financial_metrics,
            "profile": profile
        }

class ReportGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.styles = getSampleStyleSheet()
        self.normal_style = self.styles['Normal']

    def generate_llm_insights(self, results: dict) -> dict:
        profile = results.get('profile')
        if profile is None:
            return {"analysis": "Error: User profile data was not found.", "status": "error", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        prompt = f"""
        You are an expert financial advisor specializing in retirement planning. Analyze this user's profile and provide highly personalized strategic recommendations.
        Focus on actionable insights based on their specific situation.

        Detailed User Profile:
        - Age: {profile.age} years old
        - Current Monthly Income: ${profile.monthly_income:,.2f}
        - Monthly Expenses: ${profile.monthly_expenses:,.2f}
        - Current Debt: ${profile.debt:,.2f}
        - Target Retirement Age: {profile.target_retirement_age}
        - Target Monthly Retirement Income: ${profile.target_retirement_income:,.2f}
        - Occupation: {profile.occupation}
        - Education: {profile.education_level}
        - Marital Status: {profile.marital_status}
        - Number of Children: {profile.number_of_children}
        - Location: {profile.location}
        - Assets: {profile.assets}
        - Health Factors: {profile.chronic_diseases or 'None reported'}
        - Lifestyle: {profile.lifestyle_habits}

        Financial Analysis:
        - Monthly Savings Capacity: ${profile.monthly_income - profile.monthly_expenses:,.2f}
        - Years Until Target Retirement: {profile.target_retirement_age - profile.age}
        - Current Financial Readiness Ratio: {results.get('financial_ratio', 'N/A'):.2f}
        - Retirement Scenario: {results.get('scenario', 'N/A').title()}

        Please provide a detailed, personalized analysis in the following format. Use clear, professional language without asterisks or special characters:

        1. CURRENT POSITION ANALYSIS
        Financial Position:
        - Evaluate current financial standing
        - Analyze income and savings patterns
        - Review debt and asset position

        Savings Rate & Timeline:
        - Assess current savings rate
        - Evaluate retirement timeline feasibility
        - Review progress towards goals

        Portfolio Structure:
        - Current asset allocation
        - Risk exposure assessment
        - Investment diversity evaluation

        2. PERSONALIZED RECOMMENDATIONS
        Strategic Actions:
        - Immediate priorities
        - Medium-term objectives
        - Long-term goals

        Investment Framework:
        - Asset allocation strategy
        - Risk management approach
        - Portfolio rebalancing guidelines

        Financial Optimization:
        - Tax efficiency recommendations
        - Debt management strategy
        - Savings rate optimization

        3. RISK FACTORS & MITIGATION
        Primary Risk Assessment:
        - Career and income stability
        - Market exposure
        - Longevity considerations

        Protection Strategies:
        - Insurance recommendations
        - Emergency fund guidelines
        - Risk mitigation approaches

        4. LIFESTYLE CONSIDERATIONS
        Work-Life Integration:
        - Career development path
        - Lifestyle sustainability
        - Health and wellness factors

        Family Planning:
        - Current family needs
        - Future family considerations
        - Estate planning elements

        5. OPTIMIZATION OPPORTUNITIES
        Immediate Enhancements:
        - Short-term adjustments
        - Quick-win opportunities
        - Priority actions

        Long-term Optimization:
        - Strategic portfolio adjustments
        - Tax efficiency improvements
        - Retirement income optimization

        Provide clear, actionable recommendations without using asterisks or bullet points. Focus on professional, concise language.
        """

        try:
            response = self.model.generate_content(
                contents=prompt,
                generation_config=types.GenerationConfig(
                    temperature=0.4,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=1024
                )
            )
            
            analysis_text = response.text if response.text else "No analysis generated."
            
            # Clean up the text formatting
            cleaned_text = analysis_text.replace('*', '').replace('•', '-')
            
            # Format sections professionally
            formatted_sections = {}
            current_section = None
            current_content = []
            
            for line in cleaned_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a main section header
                if any(section in line.upper() for section in [
                    "CURRENT POSITION ANALYSIS",
                    "PERSONALIZED RECOMMENDATIONS",
                    "RISK FACTORS & MITIGATION",
                    "LIFESTYLE CONSIDERATIONS",
                    "OPTIMIZATION OPPORTUNITIES"
                ]):
                    if current_section:
                        formatted_sections[current_section] = '\n'.join(current_content)
                    current_section = line
                    current_content = []
                else:
                    # Clean up the line
                    line = re.sub(r'^\s*[-•]\s*', '', line)  # Remove leading bullets
                    line = re.sub(r'\s+', ' ', line)  # Normalize whitespace
                    if line:
                        current_content.append(line)
            
            # Add the last section
            if current_section and current_content:
                formatted_sections[current_section] = '\n'.join(current_content)
            
            # Combine all sections into final text
            final_text = ""
            for section, content in formatted_sections.items():
                final_text += f"\n{section}\n{content}\n"
            
            return {
                "analysis": final_text.strip(),
                "status": "success",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return {
                "analysis": f"Error generating insights: {str(e)}",
                "status": "error",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def parse_custom_format(self, input_text: str) -> dict:
        """Parse the custom format into a proper dictionary"""
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
                    if not value:
                        value = None
                    elif isinstance(value, str):
                        # Only process string values
                        str_value = str(value).lower()
                        if str_value == 'null':
                            value = None
                        elif value.isdigit():
                            value = int(value)
                        elif value.replace('.', '', 1).isdigit():
                            value = float(value)
                        elif str_value in ['true', 'false']:
                            value = str_value == 'true'
                    
                    result[key] = value
            
            return result
        except Exception as e:
            raise ValueError(f"Error parsing input format: {str(e)}")

    def create_pdf_report(self, results: dict, llm_insights: dict, output_path: str, congrat_msg: str = ""):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        story = []

        # Header
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1A5276'),
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2C3E50'),
            fontName='Helvetica'
        )
        story.append(Paragraph("RETIREMENT PLANNING ANALYSIS", title_style))
        story.append(Paragraph(
            "A Comprehensive Financial Planning Report",
            subtitle_style
        ))
        story.append(Spacer(1, 10))

        # Add congratulatory/status message below the title/subtitle
        if congrat_msg:
            congrat_style = ParagraphStyle(
                'Congrat',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#117A65'),
                spaceAfter=16,
                alignment=TA_LEFT
            )
            story.append(Paragraph(congrat_msg, congrat_style))
        story.append(Spacer(1, 10))

        # Get profile and metrics
        profile = results.get('profile')
        if profile is None:
            raise ValueError("Profile data is missing")

        metrics = results.get('financial_metrics', {})

        # Custom styles
        section_style = ParagraphStyle(
            'Section',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2874A6'),
            fontName='Helvetica-Bold'
        )
        
        subsection_style = ParagraphStyle(
            'Subsection',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#2E86C1'),
            fontName='Helvetica-Bold'
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=5,
            spaceAfter=5,
            textColor=colors.HexColor('#2C3E50'),
            fontName='Helvetica'
        )

        # Add User Profile Table
        story.append(Paragraph("USER PROFILE", section_style))
        story.append(Spacer(1, 10))
        
        profile_data = [
            ['Parameter', 'Value'],
            ['Name', profile.name_surname],
            ['Age', str(profile.age)],
            ['Gender', profile.gender or 'Not specified'],
            ['Marital Status', profile.marital_status or 'Not specified'],
            ['Number of Children', str(profile.number_of_children)],
            ['Education Level', profile.education_level or 'Not specified'],
            ['Occupation', profile.occupation or 'Not specified'],
            ['Location', profile.location or 'Not specified'],
            ['Monthly Income', f'${profile.monthly_income:,.2f}'],
            ['Monthly Expenses', f'${profile.monthly_expenses:,.2f}'],
            ['Current Debt', f'${profile.debt:,.2f}'],
            ['Assets', profile.assets or 'Not specified'],
            ['Target Retirement Age', str(profile.target_retirement_age)],
            ['Target Retirement Income', f'${profile.target_retirement_income:,.2f}']
        ]
        
        profile_table = Table(profile_data, colWidths=[200, 300])
        profile_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(profile_table)
        story.append(Spacer(1, 20))

        # Add Key Metrics Table
        story.append(Paragraph("KEY FINANCIAL METRICS", section_style))
        story.append(Spacer(1, 10))

        def calculate_retirement_readiness_score(metrics, profile):
            # Calculate score out of 100
            score = 0
            
            # Financial Readiness (40 points)
            if metrics['total_retirement_savings'] >= metrics['required_savings']:
                score += 40
            else:
                score += (metrics['total_retirement_savings'] / metrics['required_savings']) * 40
            
            # Time to Retirement (20 points)
            years_to_retire = profile.target_retirement_age - profile.age
            if years_to_retire >= 20:
                score += 20
            else:
                score += (years_to_retire / 20) * 20
            
            # Monthly Savings Rate (20 points)
            monthly_savings = profile.monthly_income - profile.monthly_expenses
            savings_rate = monthly_savings / profile.monthly_income if profile.monthly_income > 0 else 0
            score += min(savings_rate * 100, 20)
            
            # Debt Management (20 points)
            annual_income = profile.monthly_income * 12
            if annual_income > 0:
                debt_to_income = profile.debt / annual_income
                if debt_to_income <= 0.3:
                    score += 20
                else:
                    score += max(0, (1 - debt_to_income) * 20)
            
            return min(100, max(0, score))

        def get_readiness_status(score):
            if score >= 90:
                return "Excellent", colors.HexColor('#27AE60')
            elif score >= 75:
                return "Good", colors.HexColor('#2ECC71')
            elif score >= 60:
                return "Fair", colors.HexColor('#F1C40F')
            elif score >= 40:
                return "Needs Attention", colors.HexColor('#E67E22')
            else:
                return "Critical", colors.HexColor('#E74C3C')

        # Calculate additional metrics
        monthly_savings = profile.monthly_income - profile.monthly_expenses
        annual_income = profile.monthly_income * 12
        savings_rate = (monthly_savings / profile.monthly_income * 100) if profile.monthly_income > 0 else 0
        debt_to_income = (profile.debt / annual_income * 100) if annual_income > 0 else 0
        years_to_retirement = profile.target_retirement_age - profile.age
        retirement_readiness_score = calculate_retirement_readiness_score(metrics, profile)
        readiness_status, status_color = get_readiness_status(retirement_readiness_score)
        
        # Calculate retirement income replacement ratio
        target_replacement_ratio = (profile.target_retirement_income * 12) / annual_income * 100 if annual_income > 0 else 0
        
        key_metrics_data = [
            ['Category', 'Metric', 'Value', 'Status/Notes'],
            
            # Retirement Readiness Score
            ['Retirement\nReadiness', 'Overall Score', f"{retirement_readiness_score:.1f}/100", readiness_status],
            
            # Core Financial Metrics
            ['Core\nFinancials', 'Current Monthly Income', f"${profile.monthly_income:,.2f}", "Base Income"],
            ['', 'Monthly Savings', f"${monthly_savings:,.2f}", f"{savings_rate:.1f}% of Income"],
            ['', 'Annual Income', f"${annual_income:,.2f}", "Gross Amount"],
            ['', 'Debt-to-Income Ratio', f"{debt_to_income:.1f}%", 
             "Good" if debt_to_income <= 30 else "High" if debt_to_income <= 50 else "Critical"],
            
            # Retirement Projections
            ['Retirement\nProjections', 'Years to Retirement', f"{years_to_retirement} years", 
             "Long-term" if years_to_retirement > 20 else "Mid-term" if years_to_retirement > 10 else "Near-term"],
            ['', 'Total Retirement Savings', f"${metrics['total_retirement_savings']:,.2f}", "Projected"],
            ['', 'Required Savings', f"${metrics['required_savings']:,.2f}", "Target"],
            ['', 'Financial Readiness Ratio', f"{results['financial_ratio']:.2f}", 
             "On Track" if results['financial_ratio'] >= 1 else "Gap Present"],
            
            # Income Replacement
            ['Income\nReplacement', 'Target Monthly Income', f"${profile.target_retirement_income:,.2f}", "In Retirement"],
            ['', 'Income Replacement Ratio', f"{target_replacement_ratio:.1f}%", 
             "Adequate" if target_replacement_ratio >= 70 else "Review Needed"],
            ['', 'Expected Duration', f"{metrics['retirement_duration']:.1f} years", "Post-Retirement"],
            
            # Risk Metrics
            ['Risk\nMetrics', 'Life Expectancy', f"{results.get('life_expectancy', 0):.1f} years", "Estimated"],
            ['', 'Longevity Risk Buffer', 
             f"{max(0, results.get('life_expectancy', 0) - profile.target_retirement_age - metrics['retirement_duration']):.1f} years",
             "Additional Coverage"],
            ['', 'Current Scenario', results['scenario'].title(), 
             "Optimal" if results['scenario'] == 'standard_retirement' else "Adjust Plan"]
        ]
        
        # Create table with adjusted column widths
        key_metrics_table = Table(key_metrics_data, colWidths=[100, 150, 150, 130])
        key_metrics_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874A6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            
            # Category styling
            *[('BACKGROUND', (0, i), (0, i), colors.HexColor('#EBF5FB'))
              for i in range(len(key_metrics_data)) if key_metrics_data[i][0]],
            
            # General cell styling
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right align values
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Center align status
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            
            # Grid styling
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2874A6')),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Merge cells for categories - Fixed spans
            ('SPAN', (0, 1), (0, 1)),  # Retirement Readiness
            ('SPAN', (0, 2), (0, 5)),  # Core Financials
            ('SPAN', (0, 6), (0, 9)),  # Retirement Projections
            ('SPAN', (0, 10), (0, 12)), # Income Replacement
            ('SPAN', (0, 13), (0, 15)), # Risk Metrics
            
            # Status color coding
            ('TEXTCOLOR', (3, 1), (3, 1), status_color),  # Readiness status color
            *[('TEXTCOLOR', (3, i), (3, i), 
               colors.HexColor('#27AE60') if 'Good' in key_metrics_data[i][3] or 'On Track' in key_metrics_data[i][3] or 'Adequate' in key_metrics_data[i][3]
               else colors.HexColor('#E74C3C') if 'Critical' in key_metrics_data[i][3] or 'High' in key_metrics_data[i][3]
               else colors.HexColor('#F1C40F'))
              for i in range(1, len(key_metrics_data))],
            
            # Alternating row colors
            *[('BACKGROUND', (1, i), (-1, i), colors.HexColor('#F8F9F9'))
              for i in range(1, len(key_metrics_data), 2)],
        ]))
        
        # Add table description
        description_style = ParagraphStyle(
            'Description',
            parent=content_style,
            fontSize=10,
            textColor=colors.HexColor('#34495E'),
            spaceBefore=10,
            spaceAfter=10
        )
        
        metrics_description = """
        This comprehensive financial metrics dashboard provides a detailed view of your retirement readiness:
        • Overall Score: Combines financial readiness, time horizon, savings rate, and debt management
        • Core Financials: Current income, savings, and debt metrics
        • Retirement Projections: Progress towards retirement goals
        • Income Replacement: Post-retirement income analysis
        • Risk Metrics: Longevity and scenario analysis
        
        Color indicators: Green = Optimal, Yellow = Moderate, Red = Needs Attention
        """
        story.append(Paragraph(metrics_description, description_style))
        story.append(key_metrics_table)
        story.append(Spacer(1, 20))

        # Add Alternative Retirement Scenarios Table
        scenario_title_style = ParagraphStyle(
            'ScenarioTitle',
            parent=section_style,
            fontSize=20,
            textColor=colors.HexColor('#1A5276'),
            spaceBefore=15,
            spaceAfter=20,
            borderWidth=2,
            borderColor=colors.HexColor('#2874A6'),
            borderPadding=10,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("💰 ALTERNATIVE RETIREMENT SCENARIOS 📊", scenario_title_style))
        story.append(Spacer(1, 15))

        # Calculate alternative scenarios
        current_age = profile.age
        current_monthly_savings = profile.monthly_income - profile.monthly_expenses
        target_age = profile.target_retirement_age
        
        # Calculate scenarios with different retirement ages and savings rates
        scenarios_data = [
            ['Strategy', 'Retirement\nTarget', 'Required\nMonthly Savings', 'Projected\nTotal Portfolio', 'Analysis'],
        ]

        # Helper function to calculate scenario metrics
        def calculate_scenario(retirement_age, monthly_savings_multiplier):
            years_to_retire = retirement_age - current_age
            monthly_savings_amount = current_monthly_savings * monthly_savings_multiplier
            
            # Calculate future value assuming 7% annual return
            future_value = monthly_savings_amount * 12 * ((1.07 ** years_to_retire - 1) / 0.07)
            
            # Add current projected savings
            total_savings = future_value + metrics['total_retirement_savings']
            
            # Calculate income coverage (years of retirement income covered)
            annual_target_income = profile.target_retirement_income * 12
            income_coverage = total_savings / annual_target_income if annual_target_income > 0 else 0
            
            # Determine status with color
            if income_coverage >= metrics['retirement_duration']:
                status = "STRONG"
                status_color = colors.HexColor('#27AE60')  # Green
                status_bg = colors.HexColor('#E8F6F3')
            elif income_coverage >= metrics['retirement_duration'] * 0.75:
                status = "STABLE"
                status_color = colors.HexColor('#F1C40F')  # Yellow
                status_bg = colors.HexColor('#FCF3CF')
            else:
                status = "ATTENTION"
                status_color = colors.HexColor('#E74C3C')  # Red
                status_bg = colors.HexColor('#FADBD8')
            
            return [
                f"${monthly_savings_amount:,.0f}",
                f"${total_savings:,.0f}",
                status,
                status_color,
                status_bg
            ]

        # Generate scenarios
        base_scenario = calculate_scenario(target_age, 1.0)
        early_high = calculate_scenario(target_age - 5, 1.5)
        early_same = calculate_scenario(target_age - 5, 1.0)
        late_low = calculate_scenario(target_age + 5, 0.8)
        late_high = calculate_scenario(target_age + 5, 1.2)

        scenarios_data.extend([
            ['■ Base Plan', f"Age {target_age}\n({target_age - current_age} years)", *base_scenario[:-2]],
            ['■ Accelerated', f"Age {target_age - 5}\n({target_age - 5 - current_age} years)", *early_high[:-2]],
            ['■ Early Exit', f"Age {target_age - 5}\n({target_age - 5 - current_age} years)", *early_same[:-2]],
            ['■ Extended', f"Age {target_age + 5}\n({target_age + 5 - current_age} years)", *late_low[:-2]],
            ['■ Optimized', f"Age {target_age + 5}\n({target_age + 5 - current_age} years)", *late_high[:-2]]
        ])

        # Create scenarios table with enhanced styling
        scenarios_table = Table(scenarios_data, colWidths=[100, 90, 110, 130, 90])
        scenarios_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A5276')),  # Darker blue
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Grid styling
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1A5276')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1A5276')),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            
            # Enhanced padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Status colors with background tint
            *[('BACKGROUND', (4, i), (4, i), scenarios_data[i][2] == "STRONG" and colors.HexColor('#E8F6F3') or
               scenarios_data[i][2] == "STABLE" and colors.HexColor('#FCF3CF') or
               colors.HexColor('#FADBD8')) for i in range(1, len(scenarios_data))],
            
            # Strategy name styling
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            
            # Alternating row colors with subtle tint
            *[('BACKGROUND', (0, i), (3, i), colors.HexColor('#F4F6F7'))
              for i in range(1, len(scenarios_data), 2)],
            
            # Highlight base plan row
            ('BACKGROUND', (0, 1), (3, 1), colors.HexColor('#EBF5FB')),
        ]))

        # Add enhanced description for scenarios table
        scenarios_description = ParagraphStyle(
            'ScenariosDescription',
            parent=description_style,
            fontSize=9,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=12,
            spaceAfter=12,
            borderWidth=1,
            borderColor=colors.HexColor('#BDC3C7'),
            borderPadding=10,
            borderRadius=8
        )

        description_text = """
        <b>Portfolio Strategy Analysis</b>
        
        <b>Investment Strategies:</b>
        ■ <b>Base Plan:</b> Current trajectory with existing savings rate
        ■ <b>Accelerated:</b> Enhanced savings approach (150% of current rate)
        ■ <b>Early Exit:</b> Expedited retirement timeline
        ■ <b>Extended:</b> Conservative approach with reduced contributions
        ■ <b>Optimized:</b> Balanced strategy with increased savings
        
        <b>Portfolio Analysis:</b>
        • STRONG: Exceeds target portfolio requirements
        • STABLE: Meets 75-99% of portfolio objectives
        • ATTENTION: Strategic adjustments recommended
        
        <i>Analysis based on ${profile.target_retirement_income:,.2f} monthly income target
        Projections utilize 7% annualized return assumption, adjusted for inflation</i>
        """
        
        story.append(Paragraph(description_text, scenarios_description))
        story.append(scenarios_table)
        story.append(Spacer(1, 20))

        # Enhanced AI-Powered Insights Section with Gemini Analysis
        insights_title_style = ParagraphStyle(
            'InsightsTitle',
            parent=section_style,
            fontSize=20,
            textColor=colors.HexColor('#1A5276'),
            spaceBefore=15,
            spaceAfter=20,
            borderWidth=2,
            borderColor=colors.HexColor('#1A5276'),
            borderPadding=10,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("STRATEGIC PORTFOLIO INSIGHTS", insights_title_style))
        story.append(Spacer(1, 10))

        insights_style = ParagraphStyle(
            'Insights',
            parent=description_style,
            fontSize=10,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=6,
            spaceAfter=6,
            leading=14
        )

        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=insights_style,
            fontSize=12,
            textColor=colors.HexColor('#1A5276'),
            fontName='Helvetica-Bold',
            spaceBefore=12,
            spaceAfter=6
        )

        subsection_title_style = ParagraphStyle(
            'SubsectionTitle',
            parent=insights_style,
            fontSize=11,
            textColor=colors.HexColor('#2C3E50'),
            fontName='Helvetica-Bold',
            spaceBefore=8,
            spaceAfter=4
        )

        content_style = ParagraphStyle(
            'Content',
            parent=insights_style,
            fontSize=10,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=2,
            spaceAfter=4,
            leading=14
        )

        # Get AI insights from Gemini
        analysis_text = llm_insights.get('analysis', '')
        
        # Process and format the analysis
        sections = analysis_text.split('\n\n')
        for section in sections:
            if section.strip():
                lines = section.split('\n')
                if lines[0].isupper():  # Main section header
                    story.append(Paragraph(lines[0], section_title_style))
                    story.append(Spacer(1, 6))
                    
                    current_subsection = []
                    for line in lines[1:]:
                        line = line.strip()
                        if line:
                            if ':' in line and not any(char.isdigit() for char in line):  # Subsection header
                                if current_subsection:
                                    story.append(Paragraph('\n'.join(current_subsection), content_style))
                                    current_subsection = []
                                story.append(Paragraph(line, subsection_title_style))
                            else:
                                current_subsection.append(line)
                    
                    if current_subsection:
                        story.append(Paragraph('\n'.join(current_subsection), content_style))
                    
                    story.append(Spacer(1, 8))

        story.append(Spacer(1, 20))

        # Disclaimer
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=self.normal_style,
            fontSize=9,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_CENTER,
            spaceBefore=20
        )
        
        disclaimer = """
        This report is generated using AI-powered analysis and should be reviewed by a qualified financial advisor. 
        All calculations are based on provided data and industry-standard actuarial tables. 
        Past performance is not indicative of future results.
        """
        story.append(Paragraph(disclaimer, disclaimer_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Report generated on: {llm_insights['timestamp']}", disclaimer_style))
        
        # Build the PDF
        doc.build(story)

# Initialize report generator
report_generator = ReportGenerator(api_key=GEMINI_API_KEY)

def create_retirement_profile(custom_input: str):
    try:
        # Parse custom input format
        data = {}
        lines = custom_input.strip().split('\n')
        for line in lines:
            if line.strip():
                # Skip the first and last lines with curly braces
                if line.strip() in ['{', '}']:
                    continue
                # Split by first space to separate key and value
                parts = line.strip().split(' ', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().rstrip(',')  # Remove trailing comma
                    # Convert numeric values
                    if key in ['age', 'number_of_children', 'anual_working_hours', 
                             'monthly_income', 'monthly_expenses', 'debt', 
                             'target_retirement_age', 'target_retirement_income']:
                        try:
                            value = float(value)
                            if value.is_integer():
                                value = int(value)
                        except ValueError:
                            pass
                    # Convert null to None
                    elif value.lower() == 'null':
                        value = None
                    data[key] = value
        
        # Create UserProfile object
        profile = UserProfile.from_dict(data)
        
        # Calculate retirement metrics
        calculator = RetirementCalculator()
        results = calculator.recommend_retirement_age(profile)
        metrics = results['financial_metrics']
        # Extract current savings from assets if possible
        current_savings = 0.0
        if profile.assets:
            match = re.search(r'\$(\d+[\d,]*)', profile.assets)
            if match:
                current_savings = float(match.group(1).replace(',', ''))
        required_savings = metrics.get('required_savings', 0.0)
        congrat_msg = ""
        if current_savings > required_savings:
            congrat_msg = f"■ Congratulations! Your current savings of ${current_savings:,.2f} exceed the required amount of ${required_savings:,.2f}. You are fully funded for retirement and do not need additional monthly savings.\n\n"
        elif current_savings < required_savings:
            congrat_msg = f"■ Your current savings of ${current_savings:,.2f} are not sufficient to meet the required amount of ${required_savings:,.2f}. You need to save more to reach your retirement goals.\n\n"
        else:
            congrat_msg = f"■ Your current savings exactly meet the required amount for retirement (${current_savings:,.2f}).\n\n"
        
        # Generate AI insights
        llm_insights = report_generator.generate_llm_insights(results)
        
        # Generate PDF report (pass congrat_msg)
        report_filename = f"retirement_report_{profile.name_surname.replace(' ', '_')}.pdf"
        output_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, report_filename)
        report_generator.create_pdf_report(results, llm_insights, output_path, congrat_msg=congrat_msg)
        
        # Format output
        output = f"""
        {congrat_msg}📊 Retirement Analysis Results for {profile.name_surname}:
        🎯 Target Retirement Age: {results['recommended_retirement_age']} years
        💰 Financial Readiness Ratio: {results['financial_ratio']:.2f}
        📋 Scenario: {results['scenario'].title()}
        
        Financial Details:
        - Total Retirement Savings: ${results['financial_metrics']['total_retirement_savings']:,.2f}
        - Required Savings: ${results['financial_metrics']['required_savings']:,.2f}
        - Annual Retirement Expenses: ${results['financial_metrics']['annual_retirement_expenses']:,.2f}
        - Expected Retirement Duration: {results['financial_metrics']['retirement_duration']:.1f} years
        
        📝 AI-Powered Insights:
        {llm_insights['analysis']}
        
        📄 A detailed PDF report has been generated: {report_filename}
        """
        return output, output_path
    except Exception as e:
        return f"An error occurred: {str(e)}", None

# Define a function to handle the chatbot interaction

