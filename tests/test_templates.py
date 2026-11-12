from sportorg.common.template import get_text_from_file
from sportorg.models.constant import RentCards
from sportorg.models.memory import get_current_race_index, races
from sportorg.modules.backup.file import File


def test_generate_report():
    File("tests/data/test.json").open()
    races_dict = [r.to_dict() for r in races()]

    result = get_text_from_file(
        "reports/1_results.html",
        race=races_dict[get_current_race_index()],
        races=races_dict,
        rent_cards=list(RentCards().get()),
        current_race=get_current_race_index(),
        selected={"persons": []},
    )

    assert result


def test_generate_team_report_with_two_per_page_option():
    File("tests/data/test.json").open()
    races_dict = [r.to_dict() for r in races()]

    result = get_text_from_file(
        "reports/2_выписки_по_командам_универсальный.html",
        race=races_dict[get_current_race_index()],
        races=races_dict,
        rent_cards=list(RentCards().get()),
        current_race=get_current_race_index(),
        selected={"persons": []},
    )

    assert 'Две команды на листе (сверху и снизу)' in result
    assert "var HALF_PAGE_HEIGHT = '137mm';" in result
    assert "largeTeamPosition: 'top'" in result
    assert 'Большие команды располагать:' in result
    assert "currentPage.className = 'team-page team-page-pair'" in result
    assert 'element.getBoundingClientRect().height' in result
    assert "largePage.className += ' team-page-large-bottom'" in result
    assert "data-race=" in result
    assert "JSON.parse(reportElement.dataset.race)" in result
    assert "{% endraw %}" not in result
