import pytest

from sportorg import settings
from sportorg.common.template import get_text_from_file
from sportorg.models.memory import race
from sportorg.modules.backup.file import File
from sportorg.modules.printing import model
from sportorg.modules.printing import printing
from sportorg.modules.printing.printout_split import SportorgPrinter


def test_80mm_split_template_numbers_controls_from_one():
    html = get_text_from_file(
        settings.DEFAULT_SPLIT_TEMPLATE,
        race={
            "data": {"title": "Test race", "start_datetime": "2024-01-02"},
            "settings": {},
        },
        person={"surname": "Runner", "name": "Test", "bib": 1, "card_number": 2},
        result={
            "start_msec": 36000000,
            "splits": [
                {
                    "is_correct": True,
                    "course_index": 0,
                    "code": "31",
                    "relative_time": 36300000,
                    "leg_time": 300000,
                    "leg_place": 1,
                }
            ],
            "finish_msec": 36600000,
            "speed": "5:00/km",
            "rogaine_penalty": 0,
            "penalty_laps": 0,
            "penalty_time": 0,
            "result": "01:01:00",
            "place": 0,
            "status": 1,
        },
        group={"name": "M21", "count_finished": 0, "count_person": 1},
        course={"controls": []},
        organization={"name": ""},
    )

    assert "<td>1</td>" in html
    assert "<td>31</td>" in html
    assert "{{" not in html


def test_absolute_template_paths_have_split_formatting_filters(tmp_path):
    template_path = tmp_path / "custom.html"
    template_path.write_text("{{ start|tohhmmss }} {{ day|date }}", encoding="utf-8")

    html = get_text_from_file(
        str(template_path),
        start=3661000,
        day="2024-01-02",
    )

    assert html == "01:01:01 02.01.2024"


@pytest.mark.parametrize(
    "selected_template",
    [None, "Internal printing", "/split/split_printout_80mm.html"],
)
def test_split_printout_uses_80mm_template_on_macos(monkeypatch, selected_template):
    File("tests/data/test.json").open()
    obj = race()
    obj.set_setting("split_template", selected_template)
    monkeypatch.setattr(settings.SETTINGS, "printer_split", "Test printer")
    monkeypatch.setattr(model.platform, "system", lambda: "Darwin")
    printed_html = []
    monkeypatch.setattr(
        model, "print_html", lambda printer, html, **margins: printed_html.append(html)
    )

    model.split_printout(obj.results[:1])

    assert len(printed_html) == 1
    assert "ОТМЕТКА - OK" in printed_html[0]
    assert "{{" not in printed_html[0]


def test_macos_prints_in_the_main_qt_process(monkeypatch):
    class FakePrinter:
        def __init__(self):
            self.name = None
            self.margins = None

        def setPrinterName(self, name):
            self.name = name

        def isValid(self):
            return True

        def setFullPage(self, enabled):
            self.full_page = enabled

        def setPageMargins(self, *args):
            self.margins = args

        def width(self):
            return 500

        def height(self):
            return 700

    class FakeDocument:
        def setPageSize(self, size):
            self.page_size = size

        def setDocumentMargin(self, margin):
            self.margin = margin

        def setHtml(self, html):
            self.html = html

        def print_(self, printer):
            self.printer = printer

    fake_printer = FakePrinter()
    fake_document = FakeDocument()
    monkeypatch.setattr(printing.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(printing.QApplication, "instance", lambda: object())
    monkeypatch.setattr(printing, "QPrinter", lambda: fake_printer)
    monkeypatch.setattr(printing, "QTextDocument", lambda: fake_document)
    monkeypatch.setattr(printing, "QMarginsF", lambda *args: args)

    printing.print_html(
        "CETEZEN CT-S2000",
        "<html>receipt</html>",
        left=2.0,
        top=3.0,
        right=2.0,
        bottom=3.0,
    )

    assert fake_printer.name == "CETEZEN CT-S2000"
    assert fake_printer.margins[:1] == ((2.0, 3.0, 2.0, 3.0),)
    assert fake_document.html == "<html>receipt</html>"
    assert fake_document.printer is fake_printer


def test_macos_reports_an_unavailable_printer(monkeypatch):
    class InvalidPrinter:
        def setPrinterName(self, _name):
            pass

        def isValid(self):
            return False

    monkeypatch.setattr(printing.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(printing.QApplication, "instance", lambda: object())
    monkeypatch.setattr(printing, "QPrinter", InvalidPrinter)

    with pytest.raises(printing.PrinterError, match="CETEZEN CT-S2000"):
        printing.print_html("CETEZEN CT-S2000", "<html>receipt</html>")


def test_macos_uses_system_default_when_no_printer_is_selected(monkeypatch):
    class FakePrinter:
        def __init__(self):
            self.name = None

        def isValid(self):
            return True

        def setFullPage(self, _enabled):
            pass

        def setPageMargins(self, *_args):
            pass

        def width(self):
            return 500

        def height(self):
            return 700

    class FakeDocument:
        def setPageSize(self, _size):
            pass

        def setDocumentMargin(self, _margin):
            pass

        def setHtml(self, _html):
            pass

        def print_(self, _printer):
            pass

    fake_printer = FakePrinter()
    monkeypatch.setattr(printing.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(printing.QApplication, "instance", lambda: object())
    monkeypatch.setattr(printing, "QPrinter", lambda: fake_printer)
    monkeypatch.setattr(printing, "QTextDocument", FakeDocument)
    monkeypatch.setattr(printing, "QMarginsF", lambda *args: args)

    printing.print_html("", "<html>receipt</html>")

    assert fake_printer.name is None


def test_windows_printer_is_rejected_on_macos(monkeypatch):
    monkeypatch.setattr(
        "sportorg.modules.printing.printout_split.platform.system", lambda: "Darwin"
    )

    with pytest.raises(RuntimeError, match="only supported on Windows"):
        SportorgPrinter("CETEZEN CT-S2000")
