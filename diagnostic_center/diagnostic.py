from flask import Flask, request
import requests
import os

app = Flask(__name__)


# -------------------------------------------------
# Interoperability Layer
#
# The Diagnostic Center no longer communicates
# directly with the Hospital EMR.
# -------------------------------------------------

EXCHANGE_API = os.environ.get("EXCHANGE_API", "http://127.0.0.1:5003/api/exchange")
API_KEY = os.environ.get("DIAGNOSTIC_API_KEY")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "5"))

TEST_CATALOG = {
    "lvef": {"display": "Left ventricular ejection fraction", "loinc": "10230-1", "unit": "%"},
    "hemoglobin": {"display": "Hemoglobin [Mass/volume] in Blood", "loinc": "718-7", "unit": "g/dL"},
    "creatinine": {"display": "Creatinine [Mass/volume] in Serum or Plasma", "loinc": "2160-0", "unit": "mg/dL"},
    "glucose": {"display": "Glucose [Mass/volume] in Serum or Plasma", "loinc": "2345-7", "unit": "mg/dL"}
}



@app.route("/")
def home():

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Addis Diagnostic Center
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

        <div class="topbar">

            <div class="brand">
                HealthLink
            </div>

            <div class="prototype">
                Interoperability Prototype
            </div>

        </div>


        <main class="container">

            <section class="hero">

                <h1>
                    Addis Diagnostic Center
                </h1>

                <p>
                    Submit a structured diagnostic result
                    for secure exchange with the receiving
                    hospital system.
                </p>

            </section>


            <div class="layout">


                <section class="card">

                    <h2>
                        External Diagnostic Result
                    </h2>

                    <form
                        action="/send"
                        method="POST"
                    >

                        <label>
                            External Patient ID
                        </label>

                        <input
                            name="external_patient_id"
                            type="text"
                            placeholder="Example: DC-8472"
                            required
                        >


                        <label>
                            Date Performed
                        </label>

                        <input
                            name="date"
                            type="date"
                            required
                        >


                        <label>
                            Result Type
                        </label>

                        <select name="test_type" required>
                            <option value="lvef">LVEF — %</option>
                            <option value="hemoglobin">Hemoglobin — g/dL</option>
                            <option value="creatinine">Creatinine — mg/dL</option>
                            <option value="glucose">Glucose — mg/dL</option>
                        </select>

                        <label>
                            Result Value
                        </label>

                        <input
                            name="result_value"
                            type="number"
                            step="any"
                            placeholder="Enter numeric result"
                            required
                        >


                        <label>
                            Report Conclusion
                        </label>

                        <textarea
                            name="conclusion"
                            rows="5"
                            placeholder="Enter diagnostic conclusion..."
                            required
                        ></textarea>


                        <button type="submit">
                            Send Structured Result
                        </button>

                    </form>

                </section>


                <aside class="card">

                    <h2>
                        Exchange Status
                    </h2>


                    <div class="status">

                        <span class="dot"></span>

                        <span class="status-text">
                            Route: Interoperability Layer
                        </span>

                    </div>


                    <div class="status">

                        <span class="dot"></span>

                        <span class="status-text">
                            Payload: FHIR-style Bundle
                        </span>

                    </div>


                    <div class="status">

                        <span class="dot"></span>

                        <span class="status-text">
                            Authentication: API key
                        </span>

                    </div>


                    <p class="info">
                        Results are transmitted as structured
                        FHIR-style DiagnosticReport and
                        Observation resources.
                    </p>


                    <div class="flow">

                        <strong>Exchange pathway</strong>

                        <br><br>

                        Diagnostic Center

                        <br>
                        â†“

                        <br>

                        Interoperability Layer

                        <br>
                        â†“

                        <br>

                        Hospital EMR

                    </div>

                </aside>

            </div>

        </main>


        <div class="footer">

            Synthetic interoperability demonstration.
            No real patient data.

        </div>

    </body>

    </html>
    """

@app.route("/send", methods=["POST"])
def send():

    # -------------------------------------------------
    # Read form data
    # -------------------------------------------------

    patient_id = request.form["external_patient_id"]

    date = request.form["date"]
    test_type = request.form["test_type"]
    test = TEST_CATALOG.get(test_type)

    if not test:
        return "Unsupported result type.", 400

    result_value = float(request.form["result_value"])

    conclusion = request.form["conclusion"]


    # -------------------------------------------------
    # FHIR DiagnosticReport
    # -------------------------------------------------

    diagnostic_report = {

        "resourceType": "DiagnosticReport",

        "status": "final",

        "subject": {

            "identifier": {

                "system":
                    "https://example.org/diagnostic-center/patients",

                "value":
                    patient_id
            }
        },

        "effectiveDateTime":
            date,

        "conclusion":
            conclusion,

        "result": [

            {
                "reference":
                    "Observation/result-1"
            }

        ]
    }


    # -------------------------------------------------
    # FHIR Observation
    # -------------------------------------------------

    observation = {

        "resourceType":
            "Observation",

        "id":
            "result-1",

        "status":
            "final",

        # LOINC identifies the clinical concept
        "code": {

            "coding": [

                {
                    "system":
                        "http://loinc.org",

                    "code":
                        test["loinc"],

                    "display":
                        test["display"]
                }

            ],

            "text":
                test["display"]
        },

        "subject": {

            "identifier": {

                "system":
                    "https://example.org/diagnostic-center/patients",

                "value":
                    patient_id
            }
        },

        "effectiveDateTime":
            date,

        # UCUM represents the measurement unit
        "valueQuantity": {

            "value":
                result_value,

            "unit":
                test["unit"],

            "system":
                "http://unitsofmeasure.org",

            "code":
                test["unit"]
        }
    }


    # -------------------------------------------------
    # FHIR Bundle
    # -------------------------------------------------

    fhir_bundle = {

        "resourceType":
            "Bundle",

        "type":
            "collection",

        "entry": [

            {
                "resource":
                    diagnostic_report
            },

            {
                "resource":
                    observation
            }

        ]
    }


    # -------------------------------------------------
    # Send to Interoperability Layer
    #
    # Notice:
    # We do NOT send directly to the Hospital anymore.
    # -------------------------------------------------

    try:

        response = requests.post(
            EXCHANGE_API,
            json=fhir_bundle,
            headers={
                "X-API-Key": API_KEY
            },
            timeout=REQUEST_TIMEOUT
        )

        exchange_response = response.json()


    except requests.exceptions.RequestException:

        return """
        <h1>Exchange Failed</h1>

        <p>
            The Interoperability Layer
            could not be reached.
        </p>

        <p>
            Make sure it is running
            on port 5003.
        </p>

        <p>
            <a href="/">
                Try Again
            </a>
        </p>
        """


    except ValueError:

        return """
        <h1>Exchange Failed</h1>

        <p>
            The Interoperability Layer returned
            an invalid response.
        </p>

        <p>
            <a href="/">
                Try Again
            </a>
        </p>
        """


    # -------------------------------------------------
    # Successful delivery
    # -------------------------------------------------

    if response.status_code == 201:

        hospital_response = exchange_response.get(
            "hospital_response",
            {}
        )

        hospital_patient_id = hospital_response.get(
            "hospital_patient_id",
            "Unknown"
        )

        result_id = hospital_response.get(
            "result_id",
            "Unknown"
        )

        return f"""
        <h1>FHIR Result Delivered</h1>

        <p>
            The result was successfully sent through
            the Interoperability Layer and accepted
            by the Hospital EMR.
        </p>

        <p>
            <strong>Exchange Status:</strong>
            {exchange_response.get("exchange_status")}
        </p>

        <p>
            <strong>Destination:</strong>
            {exchange_response.get("destination")}
        </p>

        <p>
            <strong>Hospital Patient ID:</strong>
            {hospital_patient_id}
        </p>

        <p>
            <strong>Hospital Database Result ID:</strong>
            {result_id}
        </p>

        <p>
            <strong>HTTP Status:</strong>
            {response.status_code}
        </p>

        <p>
            <a href="/">
                Send Another Result
            </a>
        </p>
        """


    # -------------------------------------------------
    # Exchange rejected / failed
    # -------------------------------------------------

    return f"""
    <h1>FHIR Exchange Failed</h1>

    <p>
        The result was not successfully delivered.
    </p>

    <p>
        <strong>HTTP Status:</strong>
        {response.status_code}
    </p>

    <p>
        <strong>Exchange Response:</strong>
        {exchange_response}
    </p>

    <p>
        <a href="/">
            Try Again
        </a>
    </p>
    """


if __name__ == "__main__":

    app.run(
        port=5000,
        debug=True
    )





