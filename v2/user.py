user_schema = {
    "name_surname": {
        "type": "string",
        "description": "The full name of the user.",
        "required": True
    },
    "age": {
        "type": "integer",
        "description": "The age of the user.",
        "required": True
    },
    "email": {
        "type": "string",
        "description": "The email address of the user.",
        "required": True
    },
    "gender": {
        "type": "string",
        "description": "The gender of the user.",
        "options": ["Male", "Female", "Other"],
        "required": True
    },
    "marital_status": {
        "type": "string",
        "description": "The marital status of the user.",
        "options": ["Single", "Married", "Divorced", "Widowed"],
        "required": True
    },
    "number_of_children": {
        "type": "integer",
        "description": "The number of children the user has.",
        "required": True
    },
    "highest_education_level": {
        "type": "string",
        "description": "The highest level of education the user has completed.",
        "options": [
        "High School",
        "Associate's Degree",
        "Bachelor's Degree",
        "Master's Degree",
        "Doctorate",
        "Other"
        ]
    },
    "occupation": {
        "type": "string",
        "description": "The occupation of the user.",
        "required": True
    },
    "annual_working_hours": {
        "type": "integer",
        "description": "The number of hours the user works in a year.",
        "required": True
    },
    "monthly_income": {
        "type": "integer",
        "description": "The monthly income of the user.",
        "required": True
    },
    "monthly_expenses": {
        "type": "integer",
        "description": "The monthly expenses of the user.",
        "required": True
    },
    "debt": {
        "type": "integer",
        "description": "The amount of debt the user has.",
        "required": True
    },
    "assets": {
        "type": "string",
        "description": "All kind of assets the user has.",
        "required": True,
        "example": "House worth $300,000, car worth $20,000, savings of $50,000, $10,000 in stocks."
    },
    "location": {
        "type": "string",
        "description": "The location of the user.",
        "required": True
    },
    "chronic_diseases": {
        "type": "string",
        "description": "List of chronic diseases the user has.",
        "example": "Diabetes, hypertension, asthma.",
        "required": True
    },
    "lifestyle_habits": {
        "type": "string",
        "description": "List of lifestyle habits of the user.",
        "example": "Non-smoker, moderate alcohol consumption, regular exercise."
    },
    "family_health_history": {
        "type": "string",
        "description": "Family health history of the user.",
        "example": "Father had heart disease, mother had breast cancer.",
        "required": True
    },
    "target_retirement_age": {
        "type": "integer",
        "description": "The age at which the user plans to retire.",
        "required": True
    },
    "target_retirement_income": {
        "type": "integer",
        "description": "The income the user wants to have at retirement.",
        "required": True
    }
}

class User:
    """
    User class for the application.
    """
    
    def __init__(
        self,
        name_surname: str,
        email: str,
        password: str,
        age: int = None,
        gender: str = None,
        marital_status: str = None,
        number_of_children: int = None,
        highest_education_level: str = None,
        occupation: str = None,
        annual_working_hours: int = None,
        monthly_income: float = None,
        monthly_expenses: float = None,
        debt: float = None,
        assets: float = None,
        location: str = None,
        chronic_diseases: str = None,
        lifestyle_habits: str = None,
        family_health_history: str = None,
        target_retirement_age: int = None,
        target_retirement_income: float = None,
    ):
        self.name_surname = name_surname
        self.email = email
        self.password = password
        self.age = age
        self.gender = gender
        self.marital_status = marital_status
        self.number_of_children = number_of_children
        self.highest_education_level = highest_education_level
        self.occupation = occupation
        self.annual_working_hours = annual_working_hours
        self.monthly_income = monthly_income
        self.monthly_expenses = monthly_expenses
        self.debt = debt
        self.assets = assets
        self.location = location
        self.chronic_diseases = chronic_diseases
        self.lifestyle_habits = lifestyle_habits
        self.family_health_history = family_health_history
        self.target_retirement_age = target_retirement_age
        self.target_retirement_income = target_retirement_income

    def to_dict(self):
        return self.__dict__
