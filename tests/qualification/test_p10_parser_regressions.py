"""Direct-API domain obligations; no changes to the candidate or its tests."""
import pytest
from cdrse.models import SelectionProblem
from cdrse.errors import ValidationError

def input_problem(value):
    return {'model': None, 'cut_weights': [[0,0],[1,0]],
            'activation_costs': [1,1], 'constraints': {'k_min': value, 'exclude_empty': False, 'exclude_full': False}}

@pytest.mark.parametrize('value', [1.9, True, '1'])
def test_invalid_cardinality_is_rejected_before_coercion(value):
    with pytest.raises((ValidationError, ValueError, TypeError)):
        SelectionProblem.from_dict(input_problem(value)).validate()

@pytest.mark.parametrize('value', [0,1])
def test_valid_integer_cardinality_is_preserved(value):
    obj = SelectionProblem.from_dict(input_problem(value))
    obj.validate()
    assert obj.constraints.k_min == value
