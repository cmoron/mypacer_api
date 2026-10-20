import pytest
from bs4 import BeautifulSoup as bs
from fastapi import HTTPException

from mypacer_api.core import scrapper
from mypacer_api.core.scrapper import (
    ba_convert_time_to_seconds,
    parse_bases_athle_record_page,
    scrap_athlete_records,
)


def test_ba_convert_time_to_seconds():
    """
    Test the ba_convert_time_to_seconds function with various time formats.
    """
    assert ba_convert_time_to_seconds("1h30'05\"") == 5405
    assert ba_convert_time_to_seconds("30'05\"") == 1805
    assert ba_convert_time_to_seconds("30'05\"50") == 1805.5
    assert ba_convert_time_to_seconds('5"50') == 5.5


HTML_RECORDS = """
<section data-content="section_5">
<table class="grid-col-12 reveal-table base-table">
    <thead>
        <tr>
            <th>Epreuve</th>
            <th>Performance</th>
            <th>Date</th>
            <th>Categorie</th>
            <th>Club</th>
            <th>Lig./Dpt.</th>
            <th>Lieu</th>
            <th class="desktop-tablet-d-none"></th>
        </tr>
    </thead>
    <tr class="clickable">
        <td>200m</td><td>28''15 (-2.7)</td>
        <td>4 Mai 2019</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td>
        <td>La seyne sur mer</td>
        <td class="weight-bold text-blue-button desktop-tablet-d-none"></td>
    </tr>
    <tr class="detail-row hide desktop-tablet-d-none"><td colspan="4"></td></tr>
    <tr class="bg-background-light-grey clickable">
        <td>400m</td>
        <td>61''61</td>
        <td>20 Avr. 2019</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td>
        <td>La seyne sur mer</td>
        <td class="weight-bold text-blue-button desktop-tablet-d-none"></td>
    </tr>
    <tr class="detail-row hide desktop-tablet-d-none"><td colspan="4"></td></tr>
    <tr class="clickable">
        <td>800m</td>
        <td>2'23''17</td>
        <td>30 Mai 2019</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td>
        <td>Aubagne</td>
        <td class="weight-bold text-blue-button desktop-tablet-d-none"></td>
    </tr>
    <tr class="detail-row hide desktop-tablet-d-none"><td colspan="4"></td></tr>
    <tr class="bg-background-light-grey clickable">
        <td>800m Piste Courte</td>
        <td>2'23''59</td>
        <td>6 Janv. 2019</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td>
        <td>Miramas</td>
        <td class="weight-bold text-blue-button desktop-tablet-d-none"></td>
    </tr>
    <tr class="detail-row hide desktop-tablet-d-none"><td colspan="4"></td></tr>
    <tr class="clickable">
        <td>1 000m</td><td>3'08''02</td>
        <td>13 Oct. 2018</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td>
        <td>La seyne sur mer</td>
        <td class="weight-bold text-blue-button desktop-tablet-d-none"></td>
    </tr>
    <tr class="detail-row hide desktop-tablet-d-none"><td colspan="4"></td></tr>
    <tr class="bg-background-light-grey clickable">
        <td>5 Km Route</td>
        <td>18'58''</td>
        <td>3 Mars 2019</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td><td>Cannes</td><td class="weight-bold text-blue-button desktop-tablet-d-none"></td></tr>
    <tr class="detail-row hide desktop-tablet-d-none"><td colspan="4"></td></tr>
    <tr class="clickable">
        <td>10 Km Route</td>
        <td>40'03''</td>
        <td>17 Mars 2019</td>
        <td>SE</td>
        <td>A Six Fours</td>
        <td>PCA / 083</td>
        <td>Hyeres</td>
        <td class="weight-bold text-blue-button desktop-tablet-d-none"></td>
    </tr>
</table>
</section>
"""


def test_parse_bases_athle_record_page():
    """
    Test the parse_bases_athle_record_page function with a sample HTML input.
    """
    soup = bs(HTML_RECORDS, "lxml")
    records = parse_bases_athle_record_page(soup)

    assert pytest.approx(records[200], rel=1e-6) == 28.15
    assert pytest.approx(records[400], rel=1e-6) == 61.61
    assert pytest.approx(records[800], rel=1e-6) == 143.17
    assert pytest.approx(records[1000], rel=1e-6) == 188.02
    assert records[5000] == 1138
    assert records[10000] == 2403


@pytest.mark.skip(reason="This test makes a real network request and can be flaky.")
def test_scrap_athlete_records():
    """
    Test the scrap_athlete_records function with a real URL.
    """
    url = "https://www.athle.fr/athletes/2117147/records"
    records = scrap_athlete_records(url)
    assert pytest.approx(records[200], rel=1e-6) == 28.15
    assert pytest.approx(records[400], rel=1e-6) == 61.61
    assert pytest.approx(records[800], rel=1e-6) == 143.17
    assert pytest.approx(records[1000], rel=1e-6) == 188.02
    assert records[5000] == 1127
    assert records[10000] == 2403


def test_scrap_athlete_records_error(mocker):
    """
    Test that scrap_athlete_records raises an HTTPException for non-200 responses.
    """
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mocker.patch.object(scrapper.SESSION, "get", return_value=mock_response)

    # Assert that an HTTPException is raised
    with pytest.raises(HTTPException) as excinfo:
        scrap_athlete_records("http://dummyurl.com")

    # Check that the status code of the exception is correct
    assert excinfo.value.status_code == 404


def test_scrap_athlete_records_caches_successes_only(mocker):
    """Un athlète déjà consulté ne repasse pas par athle.fr ; un échec n'est pas mis en cache."""
    mocker.patch.dict(scrapper._records_cache, clear=True)
    ok = mocker.Mock(status_code=200, text=HTML_RECORDS)
    ko = mocker.Mock(status_code=503)
    get = mocker.patch.object(scrapper.SESSION, "get", side_effect=[ko, ok])

    with pytest.raises(HTTPException):
        scrap_athlete_records("https://www.athle.fr/athletes/1")
    first = scrap_athlete_records("https://www.athle.fr/athletes/1")
    second = scrap_athlete_records("https://www.athle.fr/athletes/1")

    assert first == second and first[10000] == 2403
    assert get.call_count == 2


def test_scrap_athlete_records_cache_expires(mocker):
    mocker.patch.dict(scrapper._records_cache, clear=True)
    ok = mocker.Mock(status_code=200, text=HTML_RECORDS)
    get = mocker.patch.object(scrapper.SESSION, "get", return_value=ok)
    clock = mocker.patch("mypacer_api.core.scrapper.time.monotonic", return_value=0.0)

    scrap_athlete_records("https://www.athle.fr/athletes/1")
    clock.return_value = scrapper.CACHE_TTL_SECONDS + 1
    scrap_athlete_records("https://www.athle.fr/athletes/1")

    assert get.call_count == 2
