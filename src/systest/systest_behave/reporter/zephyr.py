from typing import Dict, List, Set

from behave.model import Feature, Tag
from behave.reporter.base import Reporter

# Prefix used to identify test ID tags in features
TEST_IDENTIFICATION_PREFIX = "SIR-T"


def get_test_identification(tags: List[Tag]) -> Set[Tag]:
    """Filters and returns a set of unique test identification tags.

    Args:
        tags (list[Tag]):
    """
    return {tag for tag in tags if tag.startswith(TEST_IDENTIFICATION_PREFIX)}


class ZephyrReporter(Reporter):
    """
    A behave reporter designed to aggregate and manage test results for reporting
    to test management systems Zephyr (Jira).
    """

    def __init__(self, config):
        super(ZephyrReporter, self).__init__(config)
        self.features: List[Feature] = []
        # Store final results here (True = PASSED, False = FAILED)
        self.test_results: Dict[Tag, bool] = {}

    def feature(self, feature: Feature):
        """Called after a feature was processed.

        Args:
            feature (Feature): Feature object
        """
        self.features.append(feature)

    def build_result(self):
        # `~behave.model.Feature` attributes are:
        #     * keyword (str): This is the keyword as seen in the *feature file*. In English this will be "Feature".
        #     * name (str): The name of the feature (the text after "Feature".)
        #     * description (list[str]): The description of the feature as seen in the *feature file*. This is stored
        #                                as a list of text lines.
        #     * background (Background or NoneType): The :class:`~behave.model.Background` for this feature, if any.
        #     * scenarios (list[Scenario]): A list of :class:`~behave.model.Scenario` making up this feature.
        #     * tags (list[Tag]): A list of @tags (as :class:`~behave.model.Tag` which are basically glorified strings)
        #                         attached to the feature.
        #       See :ref:`controlling things with tags`.
        #     * status (enum 'Status'): Read-Only. A summary status of the feature's run. If read before the feature is
        #                               fully tested it will return "untested" otherwise it will return one of:
        #             Status.untested
        #                 The feature was has not been completely tested yet.
        #             Status.skipped
        #                 One or more steps of this feature was passed over during testing.
        #             Status.passed
        #                 The feature was tested successfully.
        #             Status.failed
        #                 One or more steps of this feature failed.
        #     * hook_failed (bool): Indicates if a hook failure occurred while running this feature.
        #     * duration (float): The time, in seconds, that it took to test this feature. If read before the feature
        #                         is tested it will return 0.0.
        #     * filename (str): The file name (or "<string>") of the *feature file* where the feature was found.
        #     * line (int): The line number of the *feature file* where the feature was found.
        #     * language (str): Indicates which spoken language (English, French, German, ..) was used for parsing the
        #                       feature file and its keywords. The I18N language code indicates which language is used.
        #                       This corresponds to the language tag at the beginning of the feature file.

        # `~behave.model.Scenario` attributes are:
        #     * keyword (str): This is the keyword as seen in the *feature file*. In English this will typically
        #                      be "Scenario".
        #     * name (str): The name of the scenario (the text after "Scenario:".)
        #     * description (list[str]): The description of the scenario as seen in the *feature file*. This is stored
        #                                as a list of text lines.
        #     * feature (Feature): The :class:`~behave.model.Feature` this scenario belongs to.
        #     * steps (List[Step]): A list of :class:`~behave.model.Step` making up this scenario.
        #     * tags (list[Tag]): A list of @tags (as :class:`~behave.model.Tag` which are basically glorified strings)
        #                         attached to the scenario.
        #       See :ref:`controlling things with tags`.
        #     * status (enum 'Status'): Read-Only. A summary status of the scenario's run. If read before the scenario
        #                               is fully tested it will return "untested" otherwise it will return one of:
        #             Status.untested
        #                 The scenario was has not been completely tested yet.
        #             Status.skipped
        #                 One or more steps of this scenario was passed over during testing.
        #             Status.passed
        #                 The scenario was tested successfully.
        #             Status.failed
        #                 One or more steps of this scenario failed.
        #     * hook_failed (bool): Indicates if a hook failure occurred while running this scenario.
        #     * duration (float): The time, in seconds, that it took to test this scenario. If read before the scenario
        #                         is tested it will return 0.0.
        #     * filename (str):  The file name (or "<string>") of the *feature file* where the scenario was found.
        #     * line (int): The line number of the *feature file* where the scenario was found.
        #     * parent (Feature, Rule, ...): Points to parent entity that contains this scenario.

        for feature in self.features:
            # Check if the feature passed. True if passed, False otherwise.
            for scenario in feature.scenarios:
                for tag in get_test_identification(scenario.tags):
                    if tag not in self.test_results or self.test_results[tag] is True:
                        self.test_results[tag] = scenario.status.is_passed()

            for tag in get_test_identification(feature.tags):
                if tag not in self.test_results or self.test_results[tag] is True:
                    self.test_results[tag] = feature.status.is_passed()

    def report_to_zephyr(self):
        """
        Placeholder method to send final results to the Zephyr/Jira API.
        """
        print("\n--- Zephyr Reporter Final Results ---")
        if not self.test_results:
            print("No test identifications (SIR-T) found to report.")
            return

        for test_id, passed in self.test_results.items():
            status = "PASSED" if passed else "FAILED"
            print(f"Test ID: {test_id} -> Final Status: {status}")
        print("-----------------------------------")

    def end(self):
        """
        Called after all model elements are processed.
        """
        self.build_result()
        self.report_to_zephyr()
