import gradio as gr
import global_session
import chat_interface
from user import User
from db_connector import MongoDBConnector
from user_info import create_profile_interface, get_user_info_display
from chat_interface import send_message
from agecalculatoragent import RetirementCalculator
from longevity import longevityAgent
from healthcost import HealthCostPredictorAgent
import os

os.makedirs("reports", exist_ok=True)

gemini_key = os.getenv("GENAI_KEY")
user_json = global_session.current_user.to_dict() if global_session.current_user else {}

agents = {
    "retirement": RetirementCalculator(),
    "longevity": longevityAgent(user_json),
    "health_cost": HealthCostPredictorAgent(user_json)
}
db = MongoDBConnector()

def check_auth():
    """Check if user is authenticated"""
    return global_session.current_user is not None

def signup(name_surname: str, email: str, password: str) -> tuple:
    """Handle user signup"""
    if not name_surname or not email or not password:
        return "Please provide all required fields", gr.update(visible=True), gr.update(visible=False)

    if db.add_user(name_surname, email, password):
        return "Signup successful! You can now login.", gr.update(visible=True), gr.update(visible=False)
    else:
        return "Email already exists or an error occurred", gr.update(visible=True), gr.update(visible=False)

def login(email, password):
    """Handle user login"""
    if db.verify_user(email, password):
        user_data = db.get_user(email)
        if user_data and "_id" in user_data:
            del user_data["_id"]

        if user_data:
            global_session.current_user = User(**user_data)
            chat_interface.create_chat()
            return (
                "Login successful!",
                gr.update(visible=False),  # Hide auth container
                gr.update(visible=True),   # Show main container
                *get_user_info_display()
            )
    return "Invalid email or password", gr.update(visible=True), gr.update(visible=False), *([None] * 15)

def get_retirement_report():
    user_data = get_current_user_data()
    if not user_data:
        return "Error: No user data available", None
    agents["retirement"] = RetirementCalculator(user_data)  # if constructor takes input
    report, pdf_path = agents["retirement"].handle_query()
    return report,pdf_path

def get_current_user_data():
    return global_session.current_user.to_dict() if global_session.current_user else {}

def get_longevity_report():
    user_data = get_current_user_data()
    if not user_data:
        return "Error: No user data available", None
    # Update the agent with current user data
    agents["longevity"] = longevityAgent(user_data)
    report, pdf_path = agents["longevity"].handle_query()
    return report, pdf_path

def get_health_cost_report():
    user_data = get_current_user_data()
    if not user_data:
        return "Error: No user data available", None
    agents["health_cost"] = HealthCostPredictorAgent(user_data)
    report, pdf_path = agents["health_cost"].handle_query()
    return report, pdf_path

def logout():
    """Handle user logout"""
    global_session.current_user = None
    return (
        gr.update(visible=True),   # Show auth container
        gr.update(visible=False),  # Hide main container
        *([None] * 15)            # Clear profile data
    )

def list_report_files():
    files = [f"reports/{f}" for f in os.listdir("reports") if f.endswith(".pdf")]
    return files

report_files = gr.File(label="All Report Files", file_types=[".pdf"], interactive=False, file_count="multiple")

# Örneğin sayfa yüklenince dosyaları otomatik listele:


# Create Gradio interface
with gr.Blocks(css="footer {visibility: hidden}") as app:
    # Authentication Container
    with gr.Column(visible=True) as auth_container:
        gr.Markdown("# Welcome to Retirement Planning Assistant")
        
        with gr.Tabs() as auth_tabs:
            # Signup Tab
            with gr.Tab("Sign Up"):
                signup_name_surname = gr.Textbox(label="Full Name", placeholder="Enter your full name")
                signup_email = gr.Textbox(label="Email", placeholder="Enter your email")
                signup_password = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
                signup_button = gr.Button("Sign Up", variant="primary")
                signup_message = gr.Textbox(label="Status", interactive=False)

            # Login Tab
            with gr.Tab("Login"):
                login_email = gr.Textbox(label="Email", placeholder="Enter your email")
                login_password = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
                login_button = gr.Button("Login", variant="primary")
                login_message = gr.Textbox(label="Status", interactive=False)

            
    

    # Main Application Container (initially hidden)
    with gr.Column(visible=False) as main_container:
        with gr.Row():
            gr.Markdown("# Your Assistant")
            logout_button = gr.Button("Logout", variant="secondary", scale=0)

        with gr.Tabs() as main_tabs:
            # Profile Tab
            with gr.Tab("Profile"):
                profile_components = create_profile_interface()

            # Chat Tab
            with gr.Tab("Chat"):
                gr.ChatInterface(
                    fn=send_message,
                    type="messages",
            )
        # Reports Tab
        with gr.Tab("Reports"):
                gr.Markdown("### Generate Reports:")
                with gr.Row():
                    retirement_btn = gr.Button("Retirement Report")
                    longevity_btn = gr.Button("Longevity Report")
                    health_cost_btn = gr.Button("Health Cost Report")

        report_output = gr.Textbox(label="Agent Output", lines=10, interactive=False)
        report_file = gr.File(label="Download Current PDF", interactive=False)

        gr.Markdown("### All Reports in System:")
        report_files = gr.File(label="All Report Files", file_types=[".pdf"], interactive=False, file_count="multiple")

    # Sayfa yüklenince tüm mevcut PDF'leri göster
        app.load(fn=list_report_files, outputs=report_files)

    # Wire up the components
    signup_button.click(
        fn=signup,
        inputs=[signup_name_surname, signup_email, signup_password],
        outputs=[signup_message, auth_container, main_container],
    )

    login_button.click(
        fn=login,
        inputs=[login_email, login_password],
        outputs=[login_message, auth_container, main_container, *profile_components],
    )

    logout_button.click(
        fn=logout,
        outputs=[auth_container, main_container, *profile_components],
    )

    retirement_btn.click(fn=get_retirement_report, outputs=[report_output, report_file])
    longevity_btn.click(fn=get_longevity_report, outputs=[report_output,report_file])
    health_cost_btn.click(fn=get_health_cost_report, outputs=[report_output,report_file])
                                                              
if __name__ == "__main__":
    app.launch()
