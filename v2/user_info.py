import gradio as gr
import global_session

def get_user_info_display():
    """Generate display components for user information"""
    if not global_session.current_user:
        return [
            gr.Markdown("### Please log in to view your profile"),
            None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None
        ]

    user = global_session.current_user
    user_dict = user.to_dict()

    # Basic Information
    name = user_dict.get('name_surname', 'Not provided')
    email = user_dict.get('email', 'Not provided')
    age = user_dict.get('age', 'Not provided')
    gender = user_dict.get('gender', 'Not provided')

    # Personal Details
    marital_status = user_dict.get('marital_status', 'Not provided')
    num_children = user_dict.get('number_of_children', 'Not provided')
    education = user_dict.get('education_level', 'Not provided')
    location = user_dict.get('location', 'Not provided')

    # Professional Information
    occupation = user_dict.get('occupation', 'Not provided')
    working_hours = user_dict.get('annual_working_hours', 'Not provided')
    monthly_income = user_dict.get('monthly_income', 'Not provided')
    monthly_expenses = user_dict.get('monthly_expenses', 'Not provided')

    # Financial Information
    debt = user_dict.get('debt', 'Not provided')
    assets = user_dict.get('assets', 'Not provided')

    # Health Information
    chronic_diseases = user_dict.get('chronic_diseases', 'Not provided')
    lifestyle_habits = user_dict.get('lifestyle_habits', 'Not provided')
    family_health = user_dict.get('family_health_history', 'Not provided')

    # Retirement Goals
    retirement_age = user_dict.get('target_retirement_age', 'Not provided')

    return [
        gr.Markdown(f"### Profile Information for {name}"),
        gr.Markdown("#### Basic Information"),
        gr.Markdown(f"* **Full Name:** {name}\n* **Email:** {email}\n* **Age:** {age}\n* **Gender:** {gender}"),
        gr.Markdown("#### Personal Details"),
        gr.Markdown(f"* **Marital Status:** {marital_status}\n* **Number of Children:** {num_children}\n* **Education Level:** {education}\n* **Location:** {location}"),
        gr.Markdown("#### Professional Information"),
        gr.Markdown(f"* **Occupation:** {occupation}\n* **Annual Working Hours:** {working_hours}\n* **Monthly Income:** {monthly_income}\n* **Monthly Expenses:** {monthly_expenses}"),
        gr.Markdown("#### Financial Information"),
        gr.Markdown(f"* **Debt:** {debt}\n* **Assets:** {assets}"),
        gr.Markdown("#### Health Information"),
        gr.Markdown(f"* **Chronic Diseases:** {chronic_diseases}"),
        gr.Markdown(f"* **Lifestyle Habits:** {lifestyle_habits}"),
        gr.Markdown(f"* **Family Health History:** {family_health}"),
        gr.Markdown("#### Retirement Goals"),
        gr.Markdown(f"* **Target Retirement Age:** {retirement_age}")
    ]

def create_profile_interface():
    """Create the profile interface components"""
    with gr.Column() as profile_container:
        # These components will be updated when the user logs in
        title = gr.Markdown("### Please log in to view your profile")
        
        # Basic Information Section
        basic_info_header = gr.Markdown()
        basic_info = gr.Markdown()
        
        # Personal Details Section
        personal_header = gr.Markdown()
        personal_details = gr.Markdown()
        
        # Professional Information Section
        professional_header = gr.Markdown()
        professional_info = gr.Markdown()
        
        # Financial Information Section
        financial_header = gr.Markdown()
        financial_info = gr.Markdown()
        
        # Health Information Section
        health_header = gr.Markdown()
        chronic_diseases = gr.Markdown()
        lifestyle = gr.Markdown()
        family_health = gr.Markdown()
        
        # Retirement Goals Section
        retirement_header = gr.Markdown()
        retirement_info = gr.Markdown()

    return [
        title, basic_info_header, basic_info,
        personal_header, personal_details,
        professional_header, professional_info,
        financial_header, financial_info,
        health_header, chronic_diseases,
        lifestyle, family_health,
        retirement_header, retirement_info
    ]
