"""Test MEC strategies."""
import pytest
from src.methodologies.means_end_chain.strategies.ladder_deeper import LadderDeeperStrategy
from src.methodologies.means_end_chain.strategies.clarify_relationship import ClarifyRelationshipStrategy
from src.methodologies.means_end_chain.strategies.explore_new_attribute import ExploreNewAttributeStrategy
from src.methodologies.means_end_chain.strategies.reflect_and_validate import ReflectAndValidateStrategy


@pytest.mark.asyncio
async def test_ladder_deeper_strategy():
    """Test LadderDeeperStrategy has correct metadata and signal weights."""
    strategy = LadderDeeperStrategy()
    
    assert strategy.name == "ladder_deeper"
    assert strategy.description == "Continue laddering from current concept toward terminal values"
    
    weights = strategy.score_signals()
    assert "missing_terminal_value" in weights
    assert weights["missing_terminal_value"] == 0.4
    assert weights["strategy_repetition_count"] == -0.15


@pytest.mark.asyncio
async def test_clarify_relationship_strategy():
    """Test ClarifyRelationshipStrategy has correct metadata and signal weights."""
    strategy = ClarifyRelationshipStrategy()
    
    assert strategy.name == "clarify_relationship"
    assert strategy.description == "Clarify how concepts relate to each other"
    
    weights = strategy.score_signals()
    assert "disconnected_nodes" in weights
    assert weights["disconnected_nodes"] == 0.5
    assert weights["edge_density"] == -0.3


@pytest.mark.asyncio
async def test_explore_new_attribute_strategy():
    """Test ExploreNewAttributeStrategy has correct metadata and signal weights."""
    strategy = ExploreNewAttributeStrategy()
    
    assert strategy.name == "explore_new_attribute"
    assert strategy.description == "Start exploring a new product attribute"
    
    weights = strategy.score_signals()
    assert "coverage_breadth" in weights
    assert weights["coverage_breadth"] == -0.4
    assert weights["ladder_depth"] == 0.3


@pytest.mark.asyncio
async def test_reflect_and_validate_strategy():
    """Test ReflectAndValidateStrategy has correct metadata and signal weights."""
    strategy = ReflectAndValidateStrategy()
    
    assert strategy.name == "reflect_and_validate"
    assert strategy.description == "Summarize the chain and confirm understanding"
    
    weights = strategy.score_signals()
    assert "ladder_depth" in weights
    assert weights["ladder_depth"] == 0.3
    assert weights["strategy_repetition_count"] == -0.3
