"""
Stage 2.5: SRL Preprocessing.

Extracts linguistic structure (discourse relations, SRL frames) using spaCy
to provide structural hints for the extraction stage.

This stage is optional - can be disabled via enable_srl config flag.
"""

from typing import TYPE_CHECKING, Optional

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import SrlPreprocessingOutput


if TYPE_CHECKING:
    from ..context import PipelineContext
    from src.services.srl_service import SRLService

log = structlog.get_logger(__name__)


class SRLPreprocessingStage(TurnStage):
    """
    Extract linguistic structure to guide extraction.

    If srl_service is None (feature disabled), this stage skips gracefully
    by setting an empty SrlPreprocessingOutput.
    """

    def __init__(self, srl_service: Optional["SRLService"] = None):
        """
        Initialize stage with optional SRL service.

        Args:
            srl_service: SRLService instance, or None to disable feature
        """
        self.srl_service = srl_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Extract SRL hints from user input.

        Args:
            context: Turn context with user_input and utterance_saving_output

        Returns:
            Modified context with srl_preprocessing_output set
        """
        # Validate: Stage 2 must have completed
        if not context.utterance_saving_output:
            raise RuntimeError(
                "Pipeline contract violation: SRLPreprocessingStage requires "
                "UtteranceSavingStage (Stage 2) to complete first. "
                f"Session: {context.session_id}"
            )

        # If feature is disabled, set empty output and return
        if self.srl_service is None:
            context.srl_preprocessing_output = SrlPreprocessingOutput()
            log.debug(
                "srl_preprocessing_skipped",
                session_id=context.session_id,
                reason="feature_disabled",
            )
            return context

        # Get interviewer question from recent utterances (last system utterance)
        interviewer_question: Optional[str] = None
        for utt in reversed(context.recent_utterances):
            if utt.get("speaker") == "system":
                interviewer_question = utt.get("text")
                break

        # Run SRL analysis
        analysis = self.srl_service.analyze(
            user_utterance=context.user_input, interviewer_question=interviewer_question
        )

        # Build contract output
        context.srl_preprocessing_output = SrlPreprocessingOutput(
            discourse_relations=analysis.get("discourse_relations", []),
            srl_frames=analysis.get("srl_frames", []),
        )

        log.info(
            "srl_analysis_complete",
            session_id=context.session_id,
            discourse_count=context.srl_preprocessing_output.discourse_count,
            frame_count=context.srl_preprocessing_output.frame_count,
        )

        return context
