from flask import Flask, request, jsonify

app = Flask(__name__)


# -------------------------------------------------
# Supported Clinical Terminology
# -------------------------------------------------

supported_loinc_codes = {
    "10230-1": {
        "display": "Left ventricular ejection fraction",
        "expected_ucum_unit": "%"
    },
    "718-7": {
        "display": "Hemoglobin [Mass/volume] in Blood",
        "expected_ucum_unit": "g/dL"
    },
    "2160-0": {
        "display": "Creatinine [Mass/volume] in Serum or Plasma",
        "expected_ucum_unit": "mg/dL"
    },
    "2345-7": {
        "display": "Glucose [Mass/volume] in Serum or Plasma",
        "expected_ucum_unit": "mg/dL"
    }
}

# -------------------------------------------------
# Dashboard
# -------------------------------------------------

@app.route("/")
def home():

    terminology_rows = ""

    for code, details in supported_loinc_codes.items():

        terminology_rows += f"""
        <tr>

            <td>
                <span class="code">
                    {code}
                </span>
            </td>

            <td>
                {details["display"]}
            </td>

            <td>
                <span class="code">
                    {details["expected_ucum_unit"]}
                </span>
            </td>

            <td>
                <span class="valid">
                    Supported
                </span>
            </td>

        </tr>
        """


    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            HealthLink | Terminology Service
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
                        Terminology Service
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
                        Terminology Service
                    </h1>

                    <p>
                        Validates clinical codes and measurement
                        units used in structured health data.
                    </p>

                </div>


                <div class="online">
                    Reference catalogue
                </div>

            </div>


            <section class="summary-grid">


                <div class="summary-card">

                    <div class="summary-label">
                        Supported LOINC Codes
                    </div>

                    <div class="summary-value">
                        {len(supported_loinc_codes)}
                    </div>

                </div>


                <div class="summary-card">

                    <div class="summary-label">
                        Clinical Terminology
                    </div>

                    <div class="summary-value">
                        LOINC
                    </div>

                </div>


                <div class="summary-card">

                    <div class="summary-label">
                        Unit Standard
                    </div>

                    <div class="summary-value">
                        UCUM
                    </div>

                </div>


            </section>


            <section class="term-card">


                <div class="term-header">

                    <h2>
                        Supported Clinical Concepts
                    </h2>

                    <p>
                        Terminology currently supported by this
                        learning prototype.
                    </p>

                </div>


                <table>

                    <thead>

                        <tr>
                            <th>LOINC Code</th>
                            <th>Clinical Concept</th>
                            <th>Expected UCUM Unit</th>
                            <th>Status</th>
                        </tr>

                    </thead>


                    <tbody>

                        {terminology_rows}

                    </tbody>

                </table>


            </section>


            <section class="info-card">

                <strong>
                    Why validate terminology?
                </strong>

                <br><br>

                Exchanging a value is not enough. Participating
                systems also need a shared understanding of what
                that value represents and how it is measured.

                In this prototype, LOINC identifies the clinical
                observation and UCUM represents its measurement
                unit.

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
# Terminology Validation API
# -------------------------------------------------

@app.route("/api/validate", methods=["POST"])
def validate():

    data = request.get_json()


    if not data:

        return jsonify({
            "valid": False,
            "message": "No terminology data received."
        }), 400


    coding_system = data.get("coding_system")

    code = data.get("code")

    unit_system = data.get("unit_system")

    unit_code = data.get("unit_code")


    if coding_system != "http://loinc.org":

        return jsonify({
            "valid": False,
            "message": "Unsupported coding system."
        }), 422


    terminology = supported_loinc_codes.get(code)


    if not terminology:

        return jsonify({
            "valid": False,
            "message": "Unsupported LOINC code."
        }), 422


    if unit_system != "http://unitsofmeasure.org":

        return jsonify({
            "valid": False,
            "message": "Unsupported unit system."
        }), 422


    if unit_code != terminology["expected_ucum_unit"]:

        return jsonify({
            "valid": False,
            "message":
                "Unexpected UCUM unit for this LOINC code."
        }), 422


    return jsonify({
        "valid": True,
        "code": code,
        "display": terminology["display"],
        "unit": unit_code,
        "message":
            "Clinical terminology validated."
    }), 200


if __name__ == "__main__":

    app.run(
        port=5004,
        debug=True
    )
