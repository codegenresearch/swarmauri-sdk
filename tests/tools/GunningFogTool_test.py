import pytest
from swarmauri.standard.tools.concrete.GunningFogTool import GunningFogTool as Tool

@pytest.mark.unit
def test_ubc_resource():
    tool = Tool()
    assert tool.resource == 'Tool'

@pytest.mark.unit
def test_ubc_type():
    assert Tool().type == 'GunningFogTool'

@pytest.mark.unit
def test_initialization():
    tool = Tool()
    assert type(tool.id) == str

@pytest.mark.unit
def test_serialization():
    tool = Tool()
    assert tool.id == Tool.model_validate_json(tool.model_dump_json()).id

@pytest.mark.unit
@pytest.mark.parametrize(
    "input_text, num_of_major_punctuations, num_of_words, num_of_three_plus_syllable_words",
    [
        ("This is a sample sentence. It is used to test the Gunning-Fog tool.", 2, 13),   # Test case 1
        ("Another example with more complex sentences; used for testing.", 3, 10),      # Test case 2
        ("Short sentence.", 1, 3, 0),                                                # Test case 3
        ("Punctuation-heavy text! Is it really? Yes, it is! 42", 5, 10),             # Test case 4
        ("", 0, 0)                                                                  # Test case 5: empty string
    ]
)
def test_call(input_text, num_of_major_punctuations, num_of_words, num_of_three_plus_syllable_words):
    tool = Tool()
    data = {"input_text": input_text}

    expected_score = 0.4 * (
        (num_of_words / num_of_major_punctuations) + 100 * (num_of_three_plus_syllable_words / num_of_words)
    ) if num_of_major_punctuations else 0.0

    expected_keys = {'gunning_fog_score'}

    result = tool(data)

    assert isinstance(result, dict), f"Expected dict, but got {type(result).__name__}"
    assert expected_keys.issubset(result.keys()), f"Expected keys {expected_keys} but got {result.keys()}"
    assert isinstance(result.get("gunning_fog_score"), float), f"Expected float, but got {type(result.get('gunning_fog_score')).__name__}"

    assert result.get("gunning_fog_score") == pytest.approx(expected_score, rel=0.01), f"Expected Gunning-Fog score {pytest.approx(expected_score, rel=0.01)}, but got {result.get('gunning_fog_score')}"