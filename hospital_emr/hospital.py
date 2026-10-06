from flask import Flask, request, jsonify
import requests
import sqlite3
import os

app = Flask(__name__)


# -------------------------------------------------
# Synthetic Hospital Patient Registry
# -------------------------------------------------

patients = {
    "DEMO-001": {
        "name": "Abebe Kebede",
        "date_of_birth": "1985-04-12"
    },
    "DEMO-002": {
        "name": "Hana Tesfaye",
        "date_of_birth": "1994-09-23"
    }
}


# -------------------------------------------------
# Shared Services
# -------------------------------------------------

CLIENT_REGISTRY_API = "http://127.0.0.1:5002/api/match"

TERMINOLOGY_API = "http://127.0.0.1:5004/api/validate"


# -------------------------------------------------
# Hospital Database
# -------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "hospital.db"
)


def get_database():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_database()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_patient_id TEXT NOT NULL,
            external_patient_id TEXT NOT NULL,
            date TEXT,
            conclusion TEXT,
            loinc_code TEXT NOT NULL,
            observation_name TEXT NOT NULL,
            observation_value REAL NOT NULL,
            observation_unit TEXT NOT NULL,
            source TEXT NOT NULL,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    connection.close()


initialize_database()


# -------------------------------------------------
# Home
# -------------------------------------------------

@app.route("/")
def home():

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>Hospital EMR | HealthLink</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <link
            rel="stylesheet"
            href="/static/style.css"
        >

    </head>

    <body>

        <header class="topbar">

            <div class="brand">

                <div class="logo">
                    H
                </div>

                <div>

                    <div class="brand-name">
                        HealthLink
                    </div>

                    <div class="brand-subtitle">
                        Hospital EMR
                    </div>

                </div>

            </div>

            <div class="prototype">
                Synthetic Prototype
            </div>

        </header>


        <main class="container">

            <div class="page-header">

                <div>

                    <h1>
                        Hospital EMR
                    </h1>

                    <p>
                        Receiving system for structured
                        external diagnostic results.
                    </p>

                </div>

                <div class="connected">
                    External results module
                </div>

            </div>


            <div class="result-card">

                <div class="result-body">

                    <div class="section-title">
                        External Results
                    </div>

                    <p>
                        View diagnostic results received
                        through the interoperability layer.
                    </p>

                    <p>
                        <a href="/results">
                            View External Diagnostic Results
                        </a>
                    </p>

                </div>

            </div>

        </main>


        <footer class="footer">
            Synthetic digital-health interoperability
            demonstration â€” no real patient data.
        </footer>

    </body>

    </html>
    """


# -------------------------------------------------
# Receive FHIR Result
# -------------------------------------------------

@app.route("/api/results", methods=["POST"])
def receive_result():

    bundle = request.get_json()

    if not bundle:

        return jsonify({
            "status": "error",
            "message": "No data received."
        }), 400


    if bundle.get("resourceType") != "Bundle":

        return jsonify({
            "status": "error",
            "message": "Expected a FHIR Bundle."
        }), 400


    # -------------------------------------------------
    # Find DiagnosticReport and Observation
    # -------------------------------------------------

    diagnostic_report = None
    observation = None


    for entry in bundle.get("entry", []):

        resource = entry.get("resource", {})

        if resource.get("resourceType") == "DiagnosticReport":

            diagnostic_report = resource

        elif resource.get("resourceType") == "Observation":

            observation = resource


    if not diagnostic_report:

        return jsonify({
            "status": "error",
            "message": "DiagnosticReport not found."
        }), 400


    if not observation:

        return jsonify({
            "status": "error",
            "message": "Observation not found."
        }), 400


    # -------------------------------------------------
    # Read external patient identifier
    # -------------------------------------------------

    try:

        external_patient_id = (
            diagnostic_report["subject"]["identifier"]["value"]
        )

    except (KeyError, TypeError):

        return jsonify({
            "status": "error",
            "message": "Patient identifier missing."
        }), 400


    # -------------------------------------------------
    # Ask Client Registry to resolve identity
    # -------------------------------------------------

    try:

        registry_response = requests.get(
            f"{CLIENT_REGISTRY_API}/{external_patient_id}",
            timeout=5
        )

    except requests.exceptions.RequestException:

        return jsonify({
            "status": "error",
            "message": "Client Registry could not be reached."
        }), 503


    if registry_response.status_code == 404:

        return jsonify({
            "status": "unmatched",
            "external_patient_id": external_patient_id,
            "message": "Client Registry found no patient match."
        }), 404


    if registry_response.status_code != 200:

        return jsonify({
            "status": "error",
            "message":
                "Client Registry returned an unexpected error."
        }), 503


    registry_data = registry_response.json()

    hospital_patient_id = registry_data.get(
        "hospital_patient_id"
    )


    if hospital_patient_id not in patients:

        return jsonify({
            "status": "error",
            "message":
                "Matched patient does not exist in Hospital EMR."
        }), 409


    # -------------------------------------------------
    # Extract clinical terminology
    # -------------------------------------------------

    try:

        coding = observation["code"]["coding"][0]

        coding_system = coding["system"]

        clinical_code = coding["code"]

        quantity = observation["valueQuantity"]

        observation_value = quantity["value"]

        observation_unit = quantity["unit"]

        unit_system = quantity.get("system")

        unit_code = quantity.get("code")


    except (KeyError, IndexError, TypeError):

        return jsonify({
            "status": "error",
            "message":
                "Observation terminology or value is missing."
        }), 400


    # -------------------------------------------------
    # Ask Terminology Service
    # -------------------------------------------------

    terminology_request = {
        "coding_system": coding_system,
        "code": clinical_code,
        "unit_system": unit_system,
        "unit_code": unit_code
    }


    try:

        terminology_response = requests.post(
            TERMINOLOGY_API,
            json=terminology_request,
            timeout=5
        )

    except requests.exceptions.RequestException:

        return jsonify({
            "status": "error",
            "message":
                "Terminology Service could not be reached."
        }), 503


    try:

        terminology_data = terminology_response.json()

    except ValueError:

        return jsonify({
            "status": "error",
            "message":
                "Terminology Service returned an invalid response."
        }), 503


    if terminology_response.status_code != 200:

        return jsonify({
            "status": "unsupported",
            "code": clinical_code,
            "message": terminology_data.get(
                "message",
                "Terminology validation failed."
            )
        }), 422


    if not terminology_data.get("valid"):

        return jsonify({
            "status": "unsupported",
            "code": clinical_code,
            "message":
                "Terminology Service rejected the observation."
        }), 422


    observation_name = terminology_data.get(
        "display",
        "Unknown observation"
    )


    # -------------------------------------------------
    # Store validated result
    # -------------------------------------------------

    connection = get_database()


    cursor = connection.execute(
        """
        INSERT INTO diagnostic_results (
            hospital_patient_id,
            external_patient_id,
            date,
            conclusion,
            loinc_code,
            observation_name,
            observation_value,
            observation_unit,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            hospital_patient_id,
            external_patient_id,
            diagnostic_report.get(
                "effectiveDateTime",
                "Unknown"
            ),
            diagnostic_report.get(
                "conclusion",
                ""
            ),
            clinical_code,
            observation_name,
            observation_value,
            observation_unit,
            "External Diagnostic Center"
        )
    )


    connection.commit()

    result_id = cursor.lastrowid

    connection.close()


    return jsonify({
        "status":
            "accepted",

        "result_id":
            result_id,

        "hospital_patient_id":
            hospital_patient_id,

        "external_patient_id":
            external_patient_id,

        "identity_status":
            "matched by Client Registry",

        "terminology_status":
            "validated by Terminology Service",

        "loinc_code":
            clinical_code,

        "message":
            "FHIR diagnostic result validated and stored."
    }), 201


# -------------------------------------------------
# Results Dashboard
# -------------------------------------------------

@app.route("/results")
def view_results():

    connection = get_database()

    stored_results = connection.execute(
        """
        SELECT *
        FROM diagnostic_results
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()


    total_results = len(stored_results)

    patient_ids = {
        result["hospital_patient_id"]
        for result in stored_results
    }

    total_patients = len(patient_ids)


    result_html = ""


    for result in stored_results:

        patient = patients.get(
            result["hospital_patient_id"]
        )


        if patient:

            patient_name = patient["name"]

            date_of_birth = patient["date_of_birth"]

        else:

            patient_name = "Unknown Patient"

            date_of_birth = "Unknown"


        result_html += f"""
        <article class="result-card">

            <div class="result-header">

                <div>

                    <div class="patient-name">
                        {patient_name}
                    </div>

                    <div class="patient-meta">
                        Hospital ID:
                        {result["hospital_patient_id"]}
                        &nbsp; â€¢ &nbsp;
                        DOB: {date_of_birth}
                    </div>

                </div>

                <span class="badge">
                    Validated
                </span>

            </div>


            <div class="result-body">

                <div class="section-title">
                    External Diagnostic Result
                </div>


                <div class="data-grid">


                    <div class="data-item">

                        <div class="data-label">
                            Clinical Observation
                        </div>

                        <div class="data-value">
                            {result["observation_name"]}
                        </div>

                    </div>


                    <div class="data-item">

                        <div class="data-label">
                            Result
                        </div>

                        <div class="measurement">
                            {result["observation_value"]}
                            {result["observation_unit"]}
                        </div>

                    </div>


                    <div class="data-item">

                        <div class="data-label">
                            LOINC Code
                        </div>

                        <div class="data-value">
                            {result["loinc_code"]}
                        </div>

                    </div>


                    <div class="data-item">

                        <div class="data-label">
                            External Patient ID
                        </div>

                        <div class="data-value">
                            {result["external_patient_id"]}
                        </div>

                    </div>


                    <div class="data-item">

                        <div class="data-label">
                            Source
                        </div>

                        <div class="data-value">
                            {result["source"]}
                        </div>

                    </div>


                    <div class="data-item">

                        <div class="data-label">
                            Date Performed
                        </div>

                        <div class="data-value">
                            {result["date"]}
                        </div>

                    </div>


                </div>


                <div class="conclusion">

                    <strong>
                        Report Conclusion
                    </strong>

                    <br><br>

                    {result["conclusion"]}

                </div>


                <div class="validation">

                    <span class="check">
                        Patient identity matched
                    </span>

                    <span class="check">
                        LOINC validated
                    </span>

                    <span class="check">
                        UCUM validated
                    </span>

                    <span class="check">
                        Persisted
                    </span>

                </div>


                <div
                    class="patient-meta"
                    style="margin-top: 15px;"
                >

                    Database Result #{result["id"]}

                    &nbsp; â€¢ &nbsp;

                    Received {result["received_at"]}

                </div>

            </div>

        </article>
        """


    if not stored_results:

        result_html = """
        <div class="empty">
            No external diagnostic results received.
        </div>
        """


    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Hospital EMR | HealthLink
        </title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <link
            rel="stylesheet"
            href="/static/style.css"
        >

    </head>


    <body>


        <header class="topbar">

            <div class="brand">

                <div class="logo">
                    H
                </div>

                <div>

                    <div class="brand-name">
                        HealthLink
                    </div>

                    <div class="brand-subtitle">
                        Hospital EMR
                    </div>

                </div>

            </div>


            <div class="prototype">
                Synthetic Prototype
            </div>

        </header>


        <main class="container">


            <div class="page-header">

                <div>

                    <h1>
                        External Diagnostic Results
                    </h1>

                    <p>
                        Structured results received through
                        the interoperability layer.
                    </p>

                </div>


                <div class="connected">
                    External results module
                </div>

            </div>


            <section class="summary-grid">


                <div class="summary-card">

                    <div class="summary-label">
                        Stored Results
                    </div>

                    <div class="summary-value">
                        {total_results}
                    </div>

                </div>


                <div class="summary-card">

                    <div class="summary-label">
                        Matched Patients
                    </div>

                    <div class="summary-value">
                        {total_patients}
                    </div>

                </div>


                <div class="summary-card">

                    <div class="summary-label">
                        Clinical Standards
                    </div>

                    <div class="summary-value">
                        FHIR + LOINC
                    </div>

                </div>


            </section>


            {result_html}


        </main>


        <footer class="footer">

            Synthetic digital-health interoperability
            demonstration â€” no real patient data.

        </footer>


    </body>

    </html>
    """


if __name__ == "__main__":

    app.run(
        port=5001,
        debug=True
    )
