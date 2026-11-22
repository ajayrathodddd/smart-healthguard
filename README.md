# 🛡️ Smart HealthGuard

### AI-Powered Medicine Information & Safety Assistant

Smart HealthGuard is an AI-powered web application designed to help users understand medicine-related information through intelligent analysis, OCR-based scanning, and safety insights.

The platform combines a modern React frontend with a Python FastAPI backend to provide an accessible experience for exploring medicine information, scanning medicine packaging, identifying potential safety concerns, and interacting with an AI-powered assistant.

> **Important:** Smart HealthGuard is an educational information platform. It is not a substitute for professional medical advice, diagnosis, or treatment.

---

## ✨ Key Features

### 💊 Medicine Analyzer
- Analyze medicine-related information.
- Present understandable medicine information.
- Help users explore relevant medicine details.
- Display educational safety information.

### 📷 OCR Medicine Scanner
- Scan medicine packaging and labels.
- Extract text using Optical Character Recognition (OCR).
- Process extracted text for further analysis.
- Reduce the need for manually entering medicine information.

### ⚠️ Risk Detection
- Identify potential medicine-related safety concerns.
- Present risk insights in an understandable format.
- Help users recognize information that may require professional verification.

### 🤖 AI Assistant
- AI-powered conversational assistance.
- Help users understand medicine-related information.
- Provide accessible educational explanations.

### 📊 Dashboard
- Centralized application dashboard.
- Quick access to major features.
- Organized navigation and information presentation.

### 📚 Analysis History
- Access previously saved analysis records.
- Review past activity.
- Keep medicine-related analysis organized.

### 📱 Responsive User Interface
- Modern and user-friendly interface.
- Responsive layouts for desktop, tablet, and mobile devices.
- Organized navigation and interactive components.

---

## 🧰 Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React.js, Vite, JavaScript |
| Styling | CSS3 |
| Icons | Lucide React |
| Backend | Python, FastAPI |
| Database | MongoDB |
| OCR | Tesseract OCR, Pytesseract |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn |
| API Communication | REST APIs |
| Development Tools | VS Code, Git, GitHub |

---

## 🏗️ Project Architecture

Smart HealthGuard follows a frontend-backend architecture.

```text
                 SMART HEALTHGUARD
                         |
          +--------------+--------------+
          |                             |
     FRONTEND                       BACKEND
          |                             |
     React.js                         FastAPI
       + Vite                            |
          |                    +--------+--------+
          |                    |        |        |
     User Interface          OCR    Analysis   AI Logic
          |                    |        |        |
          +--------------------+--------+--------+
                                   |
                                MongoDB
                                   |
                          Stored Application Data
```

---

## 📁 Project Structure

```text
smart-healthguard/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── assets/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── main.py
│   │   └── ...
│   └── requirements.txt
│
└── README.md
```

*The structure above is illustrative. Actual folders and files may vary as development progresses.*

---

## ⚙️ Installation & Setup

Follow these steps to run Smart HealthGuard locally.

### 1. Clone the Repository

```bash
git clone https://github.com/ajayrathodddd/smart-healthguard.git
```

### 2. Navigate to the Project

```bash
cd smart-healthguard
```

### 3. Configure the Backend

Open a terminal:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```bash
pip install -r requirements.txt
```

Configure your environment variables and MongoDB connection using the settings expected by the backend.

### 4. Start the Backend Server

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Configure the Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

### 6. Start the Frontend

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## 🔐 Environment Configuration

Smart HealthGuard may require environment variables for database connectivity and external integrations.

Create the appropriate `.env` file in the location expected by the backend and configure the required values.

Example:

```env
MONGODB_URI=your_mongodb_connection_string
```

Add other variables required by your configured integrations.

**Security:** Never commit real API keys, database credentials, passwords, private keys, or production secrets to GitHub.

---

## 🖥️ Application Modules

| Module | Purpose |
|---|---|
| Dashboard | Overview and application navigation |
| Medicine Analyzer | Medicine information analysis |
| OCR Scanner | Text extraction from medicine packaging |
| Risk Detection | Educational safety insights |
| AI Assistant | Conversational medicine information |
| Analysis History | Review previous analysis records |

---

## 🎯 Project Goals

The primary goals of Smart HealthGuard are:

- Make medicine-related educational information easier to understand.
- Explore OCR technology for medicine packaging recognition.
- Integrate AI into a practical healthcare-information application.
- Present potential safety concerns in an accessible way.
- Build a responsive and maintainable full-stack application.

---

## 🚀 Future Enhancements

Planned improvements include:

- Enhanced medicine identification and verification.
- More reliable OCR text extraction.
- Improved medicine information sources.
- Expanded safety analysis capabilities.
- Enhanced user authentication and account management.
- Improved analysis history and reporting.
- Further UI/UX and accessibility improvements.

---

## ⚠️ Medical Disclaimer

Smart HealthGuard is developed for educational and informational purposes only.

- It does not provide medical diagnoses.
- It does not prescribe medicines or dosages.
- Its analysis must not be treated as a confirmed medical assessment.
- Medicine identity, ingredients, strength, dosage form, warnings, and interactions must be verified using trustworthy sources.
- Always consult a qualified healthcare professional before making medical decisions.

---

## 👨‍💻 Developer

**Ajay Ravi Rathod**

Computer Science Engineering Student | Full-Stack Developer

- GitHub: [@ajayrathodddd](https://github.com/ajayrathodddd)
- LinkedIn: [Ajay Rathod](https://linkedin.com/in/ajay-rathod-b64467413/)
- Portfolio: [ajay-rathod-portfolio](https://ajay-rathod-portfolio-341e.vercel.app/)

---

## 📄 License

A license has not yet been specified for this repository. All rights are reserved by the project owner unless a license is added.

---

<p align="center">
  <strong>Smart HealthGuard</strong><br/>
  Making Medicine Information More Accessible Through Technology.
</p>

<p align="center">
  Built with ❤️ using React, Python, FastAPI, and MongoDB.
</p>
