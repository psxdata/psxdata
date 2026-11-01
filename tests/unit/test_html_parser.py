"""Unit tests for psxdata/parsers/html.py."""
import logging

from psxdata.parsers.html import parse_html_table, parse_tables_by_heading


def _make_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a minimal HTML table string for testing."""
    th_row = "".join(f"<th>{h}</th>" for h in headers)
    tr_rows = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{th_row}</tr></thead><tbody>{tr_rows}</tbody></table>"


class TestParseHtmlTable:
    def test_all_expected_columns_present(self):
        html = _make_table(
            ["DATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"],
            [["Jan 3, 2025", "481.99", "496.00", "474.01", "485.38", "4496408"]],
        )
        rows = parse_html_table(html)
        assert len(rows) == 1
        assert rows[0]["date"] == "Jan 3, 2025"
        assert rows[0]["open"] == "481.99"
        assert rows[0]["close"] == "485.38"

    def test_mapped_column_names(self):
        """COLUMN_MAP entries are applied — raw headers become clean names."""
        html = _make_table(["CHANGE (%)"], [["1.25"]])
        rows = parse_html_table(html)
        assert "change_pct" in rows[0]

    def test_unknown_column_gets_fallback_name_and_warns(self, caplog):
        html = _make_table(["TOTALLY_NEW_COLUMN"], [["value"]])
        with caplog.at_level(logging.WARNING):
            rows = parse_html_table(html)
        assert len(rows) == 1
        assert "totally_new_column" in rows[0]
        assert "totally_new_column" in caplog.text or "unknown" in caplog.text.lower()

    def test_missing_column_partial_mapping(self, caplog):
        """Fewer td cells than headers — row still returned with available cells."""
        html = _make_table(
            ["DATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"],
            [["Jan 3, 2025", "481.99"]],  # only 2 of 6 columns
        )
        with caplog.at_level(logging.WARNING):
            rows = parse_html_table(html)
        assert len(rows) == 1
        assert rows[0]["date"] == "Jan 3, 2025"

    def test_empty_table_returns_empty_list(self):
        html = "<table><thead><tr><th>DATE</th></tr></thead><tbody></tbody></table>"
        rows = parse_html_table(html)
        assert rows == []

    def test_empty_html_returns_empty_list(self, caplog):
        with caplog.at_level(logging.WARNING):
            rows = parse_html_table("<html></html>")
        assert rows == []

    def test_mixed_case_headers_normalized(self):
        html = _make_table(["Symbol", "Name"], [["ENGRO", "Engro Corp"]])
        rows = parse_html_table(html)
        assert "symbol" in rows[0]
        assert "name" in rows[0]

    def test_headers_with_leading_trailing_spaces(self):
        html = _make_table(["  DATE  ", "  OPEN  "], [["2024-01-01", "100"]])
        rows = parse_html_table(html)
        assert "date" in rows[0]
        assert "open" in rows[0]

    def test_multiple_rows(self):
        html = _make_table(
            ["DATE", "CLOSE"],
            [["2024-01-01", "100"], ["2024-01-02", "101"], ["2024-01-03", "102"]],
        )
        rows = parse_html_table(html)
        assert len(rows) == 3
        assert rows[2]["close"] == "102"


def _make_headed_page(sections: list[tuple[str, list[str], list[list[str]]]]) -> str:
    """Build HTML with <h2> headings followed by tables."""
    parts = []
    for heading, headers, rows in sections:
        th_row = "".join(f"<th>{h}</th>" for h in headers)
        tr_rows = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            for row in rows
        )
        parts.append(
            f"<h2>{heading}</h2>"
            f"<table><thead><tr>{th_row}</tr></thead><tbody>{tr_rows}</tbody></table>"
        )
    return "<html><body>" + "".join(parts) + "</body></html>"


class TestParseTablesByHeading:
    def test_multiple_tables_with_headings(self):
        html = _make_headed_page([
            ("T-Bills", ["SYMBOL", "NAME"], [["TB1", "Treasury Bill 1"]]),
            ("Sukuk", ["SYMBOL", "NAME"], [["SK1", "Sukuk 1"], ["SK2", "Sukuk 2"]]),
        ])
        result = parse_tables_by_heading(html)
        assert "t_bills" in result
        assert "sukuk" in result
        assert len(result["t_bills"]) == 1
        assert len(result["sukuk"]) == 2
        assert result["t_bills"][0]["symbol"] == "TB1"

    def test_table_without_heading_gets_fallback_key(self):
        html = (
            "<html><body>"
            "<table><thead><tr><th>SYMBOL</th></tr></thead>"
            "<tbody><tr><td>ENGRO</td></tr></tbody></table>"
            "</body></html>"
        )
        result = parse_tables_by_heading(html)
        assert "table_0" in result
        assert result["table_0"][0]["symbol"] == "ENGRO"

    def test_empty_html_returns_empty_dict(self):
        result = parse_tables_by_heading("<html></html>")
        assert result == {}

    def test_single_table_with_heading(self):
        html = _make_headed_page([
            ("Government Bonds", ["SYMBOL", "NAME"], [["GB1", "Govt Bond 1"]]),
        ])
        result = parse_tables_by_heading(html)
        assert len(result) == 1
        assert "government_bonds" in result
        assert result["government_bonds"][0]["name"] == "Govt Bond 1"

    def test_heading_normalized_to_snake_case(self):
        html = _make_headed_page([
            ("Term Finance Certificates", ["SYMBOL"], [["TFC1"]]),
        ])
        result = parse_tables_by_heading(html)
        assert "term_finance_certificates" in result

    def test_mixed_headed_and_unheaded_tables(self):
        html = (
            "<html><body>"
            "<table><thead><tr><th>SYMBOL</th></tr></thead>"
            "<tbody><tr><td>A</td></tr></tbody></table>"
            "<h2>Bonds</h2>"
            "<table><thead><tr><th>NAME</th></tr></thead>"
            "<tbody><tr><td>Bond X</td></tr></tbody></table>"
            "</body></html>"
        )
        result = parse_tables_by_heading(html)
        assert "table_0" in result
        assert "bonds" in result


class TestDataOrderCells:
    """PSX renders exact values in data-order; visible text is display-only."""

    _HTML = (
        "<table><thead><tr><th>SYMBOL</th><th>MARKET CAP.</th><th>PRICE</th>"
        "<th>FREE FLOAT</th></tr></thead><tbody>"
        '<tr><td data-order="BAHL"><a>BAHL</a><div class="tag">XD</div></td>'
        '<td data-order="167702981472.91">167.7B</td>'
        '<td data-order="150.89">150.89</td>'
        '<td data-order="6987575">7.0M</td></tr>'
        "</tbody></table>"
    )

    def test_symbol_ignores_tag_text(self):
        assert parse_html_table(self._HTML)[0]["symbol"] == "BAHL"

    def test_abbreviated_number_uses_data_order(self):
        row = parse_html_table(self._HTML)[0]
        assert row["market_cap"] == "167702981472.91"
        assert row["free_float"] == "6987575"

    def test_plain_number_text_unchanged(self):
        assert parse_html_table(self._HTML)[0]["price"] == "150.89"

    def test_non_abbreviated_cells_keep_text_even_with_data_order(self):
        html = (
            "<table><thead><tr><th>SYMBOL</th><th>CHANGE (%)</th></tr></thead>"
            '<tbody><tr><td>A</td><td data-order="0.4">0.40%</td></tr></tbody></table>'
        )
        assert parse_html_table(html)[0]["change_pct"] == "0.40%"
