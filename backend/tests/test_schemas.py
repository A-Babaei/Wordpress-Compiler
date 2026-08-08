import pytest
from pydantic import ValidationError

from app.schemas import RunRequest


def test_python_and_sql_are_accepted():
    assert RunRequest(language="python", code="print('hi')").language == "python"
    assert RunRequest(language="sql", code="SELECT 1;").language == "sql"


def test_matlab_is_rejected():
    """MATLAB is intentionally unsupported (see README: licensing)."""
    with pytest.raises(ValidationError):
        RunRequest(language="matlab", code="disp('hi')")
