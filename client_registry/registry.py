from flask import Flask, jsonify

app = Flask(__name__)


# -------------------------------------------------
# Synthetic Cross-System Patient Links
# -------------------------------------------------

patient_links = {
    "DC-8472": {
        "hospital_patient_id": "DEMO-001",
        "name": "Abebe Kebede"
    },

    "DC-3915": {
        "hospital_patient_id": "DEMO-002",
        "name": "Hana Tesfaye"
    }
}


# -------------------------------------------------
# Client Registry Dashboard
# -------------------------------------------------

@app.route("/")
def home():

    registry_rows = ""

    for external_id, patient in patient_links.items():

        registry_rows += f"""
        <tr>

            <td>
                <span class="identifier">
                    {external_id}
                </span>
            </td>

            <td>
                <span class="identifier">
                    {patient["hospital_patient_id"]}
                </span>
            </td>

            <td class="patient-name">
                {patient["name"]}
            </td>

            <td>
                <span class="match">
                    Linked
                </span>
            </td>

        </tr>
        """


    total_links = len(patient_links)


    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            HealthLink | Client Registry
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
                        Client Registry
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
                        Client Registry
                    </h1>

                    <p>
                        Resolves patient identifiers between
                        participating health systems.
                    </p>

                </div>


                <div class="online">
                    Identifier registry
                </div>

            </div>


            <section class="summary-grid">


                <div class="summary-card">

                    <div class="summary-label">
                        Patient Links
                    </div>

                    <div class="summary-value">
                        {total_links}
                    </div>

                </div>


                <div class="summary-card">

                    <div class="summary-label">
                        Connected Identifier Domains
                    </div>

                    <div class="summary-value">
                        2
                    </div>

                </div>


                <div class="summary-card">

                    <div class="summary-label">
                        Matching Method
                    </div>

                    <div class="summary-value">
                        Identifier Map
                    </div>

                </div>


            </section>


            <section class="registry-card">


                <div class="registry-header">

                    <h2>
                        Cross-System Patient Links
                    </h2>

                    <p>
                        Synthetic identifiers used to demonstrate
                        patient identity resolution.
                    </p>

                </div>


                <table>

                    <thead>

                        <tr>
                            <th>Diagnostic Center ID</th>
                            <th>Hospital ID</th>
                            <th>Patient</th>
                            <th>Status</th>
                        </tr>

                    </thead>


                    <tbody>

                        {registry_rows}

                    </tbody>

                </table>


            </section>


            <section class="info-card">

                <strong>
                    Why is this service needed?
                </strong>

                <br><br>

                A patient can have different identifiers in
                different health systems. The Client Registry
                allows the receiving hospital to resolve the
                external identifier to its own local patient
                identifier before the diagnostic result is stored.

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
# Patient Matching API
# -------------------------------------------------

@app.route(
    "/api/match/<external_patient_id>",
    methods=["GET"]
)
def match_patient(external_patient_id):

    match = patient_links.get(
        external_patient_id
    )


    if not match:

        return jsonify({
            "status": "not_found",
            "external_patient_id":
                external_patient_id,
            "message":
                "No patient match found."
        }), 404


    return jsonify({
        "status": "matched",
        "external_patient_id":
            external_patient_id,
        "hospital_patient_id":
            match["hospital_patient_id"],
        "name":
            match["name"]
    }), 200


if __name__ == "__main__":

    app.run(
        port=5002,
        debug=True
    )
