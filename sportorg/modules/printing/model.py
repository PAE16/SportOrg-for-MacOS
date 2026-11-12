import logging
import platform
from typing import List, Optional

from sportorg import settings
from sportorg.common.template import get_text_from_file
from sportorg.language import translate
from sportorg.models.memory import Course, Group, Organization, Result, race
from sportorg.models.result.split_calculation import GroupSplits
from sportorg.modules.printing.printing import PrinterError, print_html
from sportorg.modules.printing.printout_split import SportorgPrinter


class NoResultToPrintException(Exception):
    pass


class NoPrinterSelectedException(Exception):
    pass


def split_printout(results: List[Result]):
    obj = race()

    printer = settings.SETTINGS.printer_split

    margins = {
        "left": obj.get_setting("print_margin_left", 2.0),
        "top": obj.get_setting("print_margin_top", 2.0),
        "right": obj.get_setting("print_margin_right", 2.0),
        "bottom": obj.get_setting("print_margin_bottom", 2.0),
    }
    template_path = obj.get_setting("split_template") or settings.DEFAULT_SPLIT_TEMPLATE

    group_splits_by_group = {}

    pr: Optional[SportorgPrinter] = None
    if not str(template_path).endswith(".html"):
        if platform.system() == "Windows":
            # Internal split printout, pure python. Works faster, than jinja2 template + pdf
            size = 60  # base scale factor is 60, used win32con.MM_TWIPS MapMode (unit = 1/20 of dot, 72dpi)

            array = str(template_path).split(translate("scale") + "=")
            if len(array) > 1:
                scale = array[1]
                if scale.isdecimal():
                    size = int(scale) * size // 100

            pr = SportorgPrinter(
                printer,
                size,
                int(obj.get_setting("print_margin_left", 2.0)),
                int(obj.get_setting("print_margin_top", 2.0)),
            )
        else:
            logging.warning(
                "Internal split printing is only supported on Windows; using %s",
                settings.DEFAULT_SPLIT_TEMPLATE,
            )
            template_path = settings.DEFAULT_SPLIT_TEMPLATE

    for result in results:
        person = result.person

        if not person:
            continue

        group = person.group or Group()
        course = obj.find_course(result) or Course()
        organization = person.organization or Organization()

        if group not in group_splits_by_group:
            group_splits_by_group[group] = GroupSplits(obj, group).generate(True)
        group_splits = group_splits_by_group[group]

        result.check_who_can_win()

        if pr is not None:
            pr.print_split(result)
        else:
            template = get_text_from_file(
                template_path,
                race=obj.to_dict(),
                person=person.to_dict(),
                result=result.to_dict(),
                group=group.to_dict(),
                course=course.to_dict(),
                organization=organization.to_dict(),
                items=group_splits.to_dict(),
            )
            print_html(printer, template, **margins)

    if pr is not None:
        pr.end_doc()


def split_printout_close():
    print_html("NO_PRINTER", "CLOSE_SPLIT_PRN")
