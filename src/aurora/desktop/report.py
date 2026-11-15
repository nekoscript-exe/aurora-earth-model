"""AURORA scientific report renderer."""

from html import escape


def render_report(metrics, regional):

    variable = metrics["variable"]

    name = (
        "Vegetation dynamics"
        if variable == "NDVI"
        else "Land surface temperature"
    )

    total = metrics["regional_pixels"]
    trend = regional.get("trend")

    start, end = metrics["period"]

    def metric(label, value, color="#e7edf5"):
        return f"""
        <td width="50%" style="
            background-color:#14202d;
            padding:18px;
        ">
            <span style="color:#8da5ba;">
                {escape(label)}
            </span><br>
            <span style="font-size:26px;
                         font-weight:bold;
                         color:{color};">
                {value}
            </span>
        </td>
        """

    rows = [
        ("Increasing", metrics["significant_increase"], "#69d9bd"),
        ("Decreasing", metrics["significant_decrease"], "#ec8585"),
        ("Not significant", metrics["not_significant"], "#8da5ba"),
        ("Not evaluated", metrics["not_tested"], "#efbd76")
    ]

    distribution = ""

    for label, count, color in rows:

        percent = 100 * count / max(total, 1)

        distribution += f"""
        <tr>
            <td style="color:{color};padding:9px;">
                {label}
            </td>
            <td align="right">{count:,}</td>
            <td align="right">{percent:.2f}%</td>
        </tr>
        """

    if trend:

        slope = trend["slope_per_year"]
        p = trend["p_value"]
        low, high = trend["confidence_interval_95"]

        conclusion = (
            "Nominal statistical significance detected."
            if p < 0.05
            else "Not statistically significant at 5%."
        )

        trend_html = f"""
        <h2 style="color:#69d9bd;">
            {slope:+.6f} {escape(metrics["slope_unit"])}
        </h2>

        <p>Estimated change:
        {trend["estimated_change"]:+.6f}</p>

        <p>p-value: {p:.6f}</p>
        <p>R²: {trend["r_squared"]:.6f}</p>

        <p>Nominal 95% confidence interval:
        [{low:.6f}, {high:.6f}]</p>

        <p style="color:#efbd76;">
            {conclusion}
        </p>
        """

    else:
        trend_html = """
        <p style="color:#efbd76;">
            Insufficient observations for regional regression.
        </p>
        """

    return f"""
    <html>
    <body style="
        background-color:#080e17;
        color:#e7edf5;
        font-family:sans-serif;
    ">

    <p style="color:#69d9bd;">
        AURORA / SCIENTIFIC REPORT
    </p>

    <h1>{name}</h1>

    <p style="color:#8da5ba;">
        {escape(start)} — {escape(end)}
    </p>

    <table width="100%" cellspacing="8">
        <tr>
            {metric("Historical months", metrics["months"])}
            {metric("Data coverage", f'{metrics["mean_temporal_coverage"]:.2%}')}
        </tr>
        <tr>
            {metric("Evaluated pixels", f'{metrics["tested_pixels"]:,}')}
            {metric("Analysis time", f'{metrics["seconds"]:.2f} s')}
        </tr>
    </table>

    <h2>Spatial trend distribution</h2>

    <p>{total:,} regional pixels.</p>

    <table width="100%">
        {distribution}
    </table>

    <p style="color:#8da5ba;">
        OLS with Benjamini-Hochberg correction.
        Nominal significance threshold: 5%.
    </p>

    <hr>

    <h2>Regional trend analysis</h2>

    {trend_html}

    <hr>

    <h3>Scientific limitations</h3>

    <p style="color:#8da5ba;">
        Temporal dependence may inflate significance.
        Spatial sampling and missing observations may
        influence the estimated trends. Statistical
        associations do not establish causality.
    </p>

    </body>
    </html>
    """
