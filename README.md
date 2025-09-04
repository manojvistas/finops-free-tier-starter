# FinOps Free Tier Usage Tracker

## 📖 Introduction
Cloud computing provides flexibility but can quickly incur costs if resources exceed the Free Tier limits.  
This project implements a **FinOps dashboard** to monitor AWS Free Tier usage, detect limit breaches early, and visualize trends.

## 📝 Abstract
The solution integrates **AWS Cost Explorer**, **Python scripts**, **SQLite database**, and **Grafana dashboards**.  
It helps track resource usage, provides visibility into costs, and ensures financial governance in cloud environments.

## ⚙️ Tools Used
- **Python** – Data collection from AWS Cost Explorer API
- **SQLite** – Lightweight database to store usage and cost data
- **Grafana** – Dashboard for visualization and alerts
- **AWS** – Cloud provider (Free Tier usage and billing data)

## 🚀 Steps to Run the Project
1. Clone the repository and navigate into the project folder.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   . .venv/Scripts/Activate.ps1    # On Windows PowerShell
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Fetch AWS cost data:

bash
Copy code
python scripts/fetch_aws_costs.py
This populates the SQLite database (data/finops.db).

Connect Grafana to the SQLite database.

Create dashboards:

Cost trend over time

Service-wise cost breakdown

Free Tier breach alerts

📊 Deliverables
Python scripts for cost data ingestion (scripts/fetch_aws_costs.py)

SQLite database (data/finops.db)

Grafana dashboards (time series, pie chart, alerts)

Project report (see below)

📄 Project Report
A short project report (1–2 pages) is included here:
👉 FinOps_Project_Report.pdf

✅ Conclusion
This project demonstrates a simple but effective FinOps monitoring system.
By combining Python, SQLite, and Grafana, it provides visibility into AWS Free Tier usage, ensures costs stay under control, and allows proactive alerting when usage approaches limits.
