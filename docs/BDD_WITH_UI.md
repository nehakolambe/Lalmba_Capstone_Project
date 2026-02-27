# BDD Scenarios with UI

## Feature: Lalmba Matoso chatbot core user flow

### Scenario 1: User logs in successfully
Given the user is on the Login page  
![Login](ui/login.png)

When the user enters username + PIN and clicks Login

Then the user sees the Home screen  
![Home](ui/home.png)

### Scenario 2: New user registers and completes onboarding
Given the user is on the Register page  
![Register](ui/register.png)

When the user creates an account

Then the questionnaire is shown  
![Questionnaire](ui/questionnaire.png)

And after submitting, the user can start a chat  
![Empty Chat](ui/empty-chat.png)

### Scenario 3: Returning user resumes chat history
Given the user is on the Home screen  
![Home](ui/home.png)

When the user clicks Resume Chat

Then previous messages appear  
![Chat](ui/chat.png)

And data exists in SQLite  
![DB Messages](ui/db-messages.png)

### Scenario 4: User starts a new chat session
Given the user is on the Home screen  
![Home](ui/home.png)

When the user clicks Start New Chat

Then chat history is cleared and the empty chat screen appears  
![Reset Result](ui/reset.png)

### Scenario 5: Backend unavailable
Given the user opens the app

When the backend is not reachable

Then the UI shows a "cannot connect" error and offers retry  
![Cannot Connect Error](ui/error-cannot-connect.png)
