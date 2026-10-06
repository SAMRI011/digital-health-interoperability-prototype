from flask import Flask, request, jsonify
import requests
import sqlite3
import os

app = Flask(__name__)


# -------------------------------------------------
# Configuration
# -------------------------------------------------

HOSPITAL_API = os.environ.get("HOSPITAL_API", "http://127.0.0.1:5001/api/results")

DIAGNOSTIC_CENTER_URL = os.environ.get("DIAGNOSTIC_CENTER_URL", "http://127.0.0.1:5000")
HOSPITAL_URL = os.environ.get("HOSPITAL_URL", "http://127.0.0.1:5001")
CLIENT_REGISTRY_URL = os.environ.get("CLIENT_REGISTRY_URL", "http://127.0.0.1:5002")
TERMINOLOGY_URL = os.environ.get("TERMINOLOGY_URL", "http://127.0.0.1:5004")

DIAGNOSTIC_API_KEY = os.environ.get("DIAGNOSTIC_API_KEY")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "5"))


if not DIAGNOSTIC_API_KEY:
    raise RuntimeError(
        "DIAGNOSTIC_API_KEY environment variable is required."
    )


AUTHORIZED_SYSTEMS = {
    DIAGNOSTIC_API_KEY: "Addis Diagnostic Center"
}


# -------------------------------------------------
# Database
# -------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "exchange.db"
)


def get_database():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_database()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS exchange_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_system TEXT NOT NULL,
            destination_system TEXT NOT NULL,
            resource_type TEXT,
            status TEXT NOT NULL,
            http_status INTEGER,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    connection.close()


initialize_database()


# -------------------------------------------------
# Health Check Helper
#
# This actually contacts each service.
# -------------------------------------------------

def check_service(url):

    try:

        response = requests.get(
            url,
            timeout=1
        )

        return response.status_code < 500

    except requests.exceptions.RequestException:

        return False


# -------------------------------------------------
# Dashboard
# -------------------------------------------------

@app.route("/")
def home():

    services = [
        {
            "name": "Diagnostic Center",
            "description": "External diagnostic sender",
            "online": check_service(DIAGNOSTIC_CENTER_URL)
        },
        {
            "name": "Hospital EMR",
            "description": "Receiving clinical system",
            "online": check_service(HOSPITAL_URL)
        },
        {
            "name": "Client Registry",
            "description": "Cross-system patient identity",
            "online": check_service(CLIENT_REGISTRY_URL)
        },
        {
            "name": "Terminology Service",
            "description": "LOINC and UCUM validation",
            "online": check_service(TERMINOLOGY_URL)
        }
    ]


    service_html = ""

    for service in services:

        status_class = (
            "online"
            if service["online"]
            else "offline"
        )

        status_text = (
            "Online"
            if service["online"]
            else "Offline"
        )

        service_html += f"""
        <div class="service-card">

            <div class="service-name">
                {service["name"]}
            </div>

            <div class="service-description">
                {service["description"]}
            </div>

            <div class="{status_class}">
                {status_text}
            </div>

        </div>
        """


    connection = get_database()

    exchanges = connection.execute(
        """
        SELECT *
        FROM exchange_log
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    connection.close()


    exchange_rows = ""


    for exchange in exchanges:

        status_class = (
            "status-" +
            exchange["status"].replace(
                "rejected_by_destination",
                "rejected"
            )
        )

        exchange_rows += f"""
        <tr>

            <td>
                #{exchange["id"]}
            </td>

            <td>
                {exchange["source_system"]}
            </td>

            <td>
                {exchange["destination_system"]}
            </td>

            <td>
                {exchange["resource_type"]}
            </td>

            <td class="{status_class}">
                {exchange["status"]}
            </td>

            <td>
                {exchange["http_status"]}
            </td>

            <td>
                {exchange["created_at"]}
            </td>

        </tr>
        """


    if not exchanges:

        exchange_rows = """
        <tr>
            <td colspan="7" class="empty">
                No exchanges recorded.
            </td>
        </tr>
        """


    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            HealthLink | Interoperability Dashboard
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
                        Interoperability Layer
                    </div>

                </div>

            </div>


            <div class="prototype">
                Synthetic Prototype
            </div>

        </header>


        <main class="container">

            <div class="page-header">

                <h1>
                    Interoperability Dashboard
                </h1>

                <p>
                    Monitor connected services and
                    health-information exchanges.
                </p>

            </div>


            <h2 class="section-title">
                Connected Services
            </h2>


            <section class="service-grid">

                {service_html}

            </section>


            <h2 class="section-title">
                Exchange Architecture
            </h2>


            <section class="flow">

                Diagnostic Center

                <span class="arrow">
                    â†’
                </span>

                Interoperability Layer

                <span class="arrow">
                    â†’
                </span>

                Hospital EMR

                <br>

                Hospital EMR

                <span class="arrow">
                    â†’
                </span>

                Client Registry

                &nbsp;&nbsp; + &nbsp;&nbsp;

                Terminology Service

            </section>


            <h2 class="section-title">
                Recent Exchanges
            </h2>


            <section class="table-card">

                <table>

                    <thead>

                        <tr>
                            <th>ID</th>
                            <th>Authenticated Source</th>
                            <th>Destination</th>
                            <th>FHIR Resource</th>
                            <th>Status</th>
                            <th>HTTP</th>
                            <th>Time</th>
                        </tr>

                    </thead>


                    <tbody>

                        {exchange_rows}

                    </tbody>

                </table>

            </section>

        </main>


        <footer class="footer">

            Synthetic digital-health interoperability
            demonstration â€” no real patient data.

        </footer>

    </body>

    </html>
    """


# -------------------------------------------------
# Exchange Endpoint
# -------------------------------------------------

@app.route("/api/exchange", methods=["POST"])
def exchange():

    api_key = request.headers.get("X-API-Key")

    source_system = AUTHORIZED_SYSTEMS.get(api_key)


    if not source_system:

        log_exchange(
            source="Unknown / Unauthorized",
            destination="Hospital EMR",
            resource_type="Unknown",
            status="authentication_failed",
            http_status=401,
            message="Invalid or missing API key."
        )

        return jsonify({
            "status": "unauthorized",
            "message": "Invalid or missing API key."
        }), 401


    bundle = request.get_json()


    if not bundle:

        log_exchange(
            source=source_system,
            destination="Hospital EMR",
            resource_type="Unknown",
            status="rejected",
            http_status=400,
            message="No JSON data received."
        )

        return jsonify({
            "status": "rejected",
            "message": "No JSON data received."
        }), 400


    resource_type = bundle.get("resourceType")


    if resource_type != "Bundle":

        log_exchange(
            source=source_system,
            destination="Hospital EMR",
            resource_type=resource_type or "Unknown",
            status="rejected",
            http_status=400,
            message="Expected FHIR Bundle."
        )

        return jsonify({
            "status": "rejected",
            "message": "Expected FHIR Bundle."
        }), 400


    entries = bundle.get("entry", [])


    if not entries:

        log_exchange(
            source=source_system,
            destination="Hospital EMR",
            resource_type="Bundle",
            status="rejected",
            http_status=400,
            message="FHIR Bundle contains no entries."
        )

        return jsonify({
            "status": "rejected",
            "message": "FHIR Bundle contains no entries."
        }), 400


    try:

        hospital_response = requests.post(
            HOSPITAL_API,
            json=bundle,
            timeout=REQUEST_TIMEOUT
        )

    except requests.exceptions.RequestException:

        log_exchange(
            source=source_system,
            destination="Hospital EMR",
            resource_type="Bundle",
            status="failed",
            http_status=503,
            message="Hospital EMR could not be reached."
        )

        return jsonify({
            "status": "failed",
            "message": "Hospital EMR could not be reached."
        }), 503


    try:

        hospital_data = hospital_response.json()

    except ValueError:

        hospital_data = {
            "message": "Hospital returned an invalid response."
        }


    if hospital_response.status_code == 201:

        exchange_status = "delivered"

    else:

        exchange_status = "rejected_by_destination"


    log_exchange(
        source=source_system,
        destination="Hospital EMR",
        resource_type="Bundle",
        status=exchange_status,
        http_status=hospital_response.status_code,
        message=hospital_data.get(
            "message",
            "No message returned."
        )
    )


    return jsonify({
        "exchange_status":
            exchange_status,

        "authenticated_sender":
            source_system,

        "destination":
            "Hospital EMR",

        "destination_http_status":
            hospital_response.status_code,

        "hospital_response":
            hospital_data
    }), hospital_response.status_code


# -------------------------------------------------
# Audit Logging
# -------------------------------------------------

def log_exchange(
    source,
    destination,
    resource_type,
    status,
    http_status,
    message
):

    connection = get_database()

    connection.execute(
        """
        INSERT INTO exchange_log (
            source_system,
            destination_system,
            resource_type,
            status,
            http_status,
            message
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source,
            destination,
            resource_type,
            status,
            http_status,
            message
        )
    )

    connection.commit()

    connection.close()


# -------------------------------------------------
# Existing Logs URL
# -------------------------------------------------

@app.route("/logs")
def logs():

    return """
    <h1>Exchange Logs</h1>

    <p>
        Exchange history is now displayed on the
        main interoperability dashboard.
    </p>

    <p>
        <a href="/">
            Open Dashboard
        </a>
    </p>
    """


if __name__ == "__main__":

    app.run(
        port=5003,
        debug=True
    )






