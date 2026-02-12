    def create_signal_detector(
        self, config: MethodologyConfig, llm_client: Optional[Any] = None
    ) -> "ComposedSignalDetector":
        """Create a composed signal detector for a methodology.

        Instantiates all signal detectors from methodology config.
        Args:
            config: MethodologyConfig loaded from YAML
            llm_client: Optional LLM client for batch LLM signal detection

        Returns:
            ComposedSignalDetector that detects all methodology signals,
            with LLM client configured for batch signal detection if provided.
        """
        return ComposedSignalDetector(config, llm_client=llm_client)
