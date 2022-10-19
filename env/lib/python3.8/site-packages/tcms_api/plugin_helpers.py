# Copyright (c) 2019-2021 Alexander Todorov <atodorov@MrSenko.com>

import os
from datetime import datetime

from . import TCMS


class Backend:  # pylint: disable=too-many-instance-attributes

    """
        Facilitates RPC communications with the backend and implements
        behavior described at:
        http://kiwitcms.org/blog/atodorov/2018/11/05/test-runner-plugin-specification/

        This class is intended to be used by Kiwi TCMS plugins implemented in
        Python. The plugin will call::

            backend = Backend()
            backend.configure()

            ... parse test results ...

            test_case_id, _ = backend.test_case_get_or_create(<description>)
            backend.add_test_case_to_plan(test_case_id, backend.plan_id)
            test_executions = backend.add_test_case_to_run(test_case_id,
                                                           backend.run_id)
            for execution in test_executions:
                backend.update_test_execution(execution['id'],
                                              <status_id>,
                                              <comment>)

        :param prefix: Prefix which will be added to TestPlan.name and
                       TestRun.summary

                       .. versionadded:: 5.2
        :type prefix: str
    """

    _statuses = {}

    def __init__(self, prefix=''):
        """
            :param prefix: Prefix which will be added to TestPlan.name and
                           TestRun.summary

                           .. versionadded:: 5.2
            :type prefix: str
        """
        self.prefix = prefix

        self.rpc = None
        self.run_id = None
        self.plan_id = None
        self.product_id = None
        self.category_id = None
        self.priority_id = None
        self.confirmed_id = None

    def configure(self):
        """
            This method is reading all the configs from the environment
            and will create necessary TestPlan and TestRun containers!

            One of the main reasons for it is that
            :py:attr:`tcms_api.tcms_api.TCMS.exec` will try to connect
            immediately to Kiwi TCMS!

            .. important::

                Test runner plugins **must** call this method after
                initializing the backend object and **before** calling
                any of the other methods!
        """
        self.rpc = TCMS().exec

        self.run_id = self.get_run_id()
        self.plan_id = self.get_plan_id(self.run_id)
        self.product_id, _ = self.get_product_id(self.plan_id)

        self.category_id = self.rpc.Category.filter({
            'product': self.product_id
        })[0]['id']
        self.priority_id = self.rpc.Priority.filter({})[0]['id']
        self.confirmed_id = self.rpc.TestCaseStatus.filter({
            'name': 'CONFIRMED'
        })[0]['id']

    def get_statuses_by_weight(self, lookup_condition):
        """
         Get a list of statuses based on lookup condition.

         :param lookup_condition: ``tcms.testruns.models.TestExecutionStatus``
            lookup condition
         :type lookup_condition: dict
         :rtype: list
        """
        return self.rpc.TestExecutionStatus.filter(lookup_condition)

    def get_status_id_fallback(self, name):
        """
        Get status based on weight if name not found

        :param name: ``tcms.testruns.models.TestExecutionStatus`` name
        :type name: str
        :rtype: int
        """
        if name in ['PASSED', 'WAIVED']:
            lookup_condition = 'weight__gt'
        elif name in ['FAILED', 'ERROR']:
            lookup_condition = 'weight__lt'
        return self.get_statuses_by_weight({lookup_condition: 0})[0]['id']

    def get_status_id(self, name):
        """
            Get the PK of ``tcms.testruns.models.TestExecutionStatus``
            matching the test execution status name or fallback based on
            weight.

            .. important::

                Test runner plugins **must** call this method like so::

                    id = backend.get_status_id('FAILED')

            :param name: ``tcms.testruns.models.TestExecutionStatus`` name
            :type name: str
            :rtype: int
        """
        if name not in self._statuses:
            try:
                self._statuses[name] = self.rpc.TestExecutionStatus.filter({
                    'name': name
                })[0]['id']
            except IndexError:
                self._statuses[name] = self.get_status_id_fallback(name)
        return self._statuses[name]

    def get_product_id(self, plan_id):
        """
            Return a ``tcms.management.models.Product`` PK.

            .. warning::

                For internal use by `.configure()`!

            :param plan_id: ``tcms.testplans.models.TestPlan`` PK
            :type plan_id: int
            :rtype: int

            Order of precedence:

            - `plan_id` is specified, then use TestPlan.product, otherwise
            - use `$TCMS_PRODUCT` as Product.name if specified, otherwise
            - use `$TRAVIS_REPO_SLUG` as Product.name if specified, otherwise
            - use `$JOB_NAME` as Product.name if specified

            If Product doesn't exist in the database it will be created with
            the first ``tcms.management.models.Classification`` found!
        """
        product_id = None
        product_name = None

        test_plan = self.rpc.TestPlan.filter({'pk': plan_id})
        if test_plan:
            product_id = test_plan[0]['product']
            product_name = test_plan[0]['product__name']
        else:
            product_name = os.environ.get('TCMS_PRODUCT',
                                          os.environ.get('TRAVIS_REPO_SLUG',
                                                         os.environ.get(
                                                             'JOB_NAME')))
            if not product_name:
                raise Exception('Product name not defined, '
                                'missing one of TCMS_PRODUCT, '
                                'TRAVIS_REPO_SLUG or JOB_NAME')

            product = self.rpc.Product.filter({'name': product_name})
            if not product:
                class_id = self.rpc.Classification.filter({})[0]['id']
                product = [self.rpc.Product.create({
                    'name': product_name,
                    'classification': class_id
                })]
            product_id = product[0]['id']

        return product_id, product_name

    def get_version_id(self, product_id):
        """
            Return a ``tcms.management.models.Version`` (PK, name).

            .. warning::

                For internal use by `.configure()`!

            :param product_id: ``tcms.management.models.Product`` PK
                               for which to look for Version
            :type product_id: int
            :return: (version_id, version_value)
            :rtype: tuple(int, str)

            Order of precedence:

            - use `$TCMS_PRODUCT_VERSION` as Version.value if specified, or
            - use `$TRAVIS_COMMIT` as Version.value if specified, otherwise
            - use `$TRAVIS_PULL_REQUEST_SHA` as Version.value if specified,
              otherwise
            - use `$GIT_COMMIT` as Version.value if specified

            If Version doesn't exist in the database it will be created with
            the specified `product_id`!
        """
        version_val = os.environ.get(
            'TCMS_PRODUCT_VERSION',
            os.environ.get('TRAVIS_COMMIT',
                           os.environ.get('TRAVIS_PULL_REQUEST_SHA',
                                          os.environ.get('GIT_COMMIT'))))
        if not version_val:
            raise Exception('Version value not defined, '
                            'missing one of TCMS_PRODUCT_VERSION, '
                            'TRAVIS_COMMIT, TRAVIS_PULL_REQUEST_SHA '
                            'or GIT_COMMIT')

        version = self.rpc.Version.filter({'product': product_id,
                                           'value': version_val})
        if not version:
            version = [self.rpc.Version.create({'product': product_id,
                                                'value': version_val})]

        return version[0]['id'], version_val

    def get_build_id(self, version_id):
        """
            Return a ``tcms.management.models.Build`` (PK, name).

            .. warning::

                For internal use by `.configure()`!

            :param version_id: ``tcms.management.models.Version`` PK
                               for which to look for Build
            :type version_id: int
            :return: (build_id, build_name)
            :rtype: tuple(int, str)

            Order of precedence:

            - use `$TCMS_BUILD` as Build.name if specified, otherwise
            - use `$TRAVIS_BUILD_NUMBER` as Build.name if specified, otherwise
            - use `$BUILD_NUMBER` as Build.name if specified

            If Build doesn't exist in the database it will be created with the
            specified `version_id`!
        """
        build_number = os.environ.get('TCMS_BUILD',
                                      os.environ.get('TRAVIS_BUILD_NUMBER',
                                                     os.environ.get(
                                                         'BUILD_NUMBER')))
        if not build_number:
            raise Exception('Build number not defined, '
                            'missing one of TCMS_BUILD, '
                            'TRAVIS_BUILD_NUMBER or BUILD_NUMBER')

        build = self.rpc.Build.filter({'name': build_number,
                                       'version': version_id})
        if not build:
            build = [self.rpc.Build.create({'name': build_number,
                                            'version': version_id})]

        return build[0]['id'], build_number

    def get_plan_type_id(self):
        """
            Return an **Integration** PlanType.

            .. warning::

                For internal use by `.configure()`!

            :return: ``tcms.testplans.models.PlanType`` PK
            :rtype: int
        """
        plan_type = self.rpc.PlanType.filter({'name': 'Integration'})
        if not plan_type:
            plan_type = [self.rpc.PlanType.create({'name': 'Integration'})]

        return plan_type[0]['id']

    def external_plan_id(self):  # pylint: disable=no-self-use
        """
            Allows the user to specify `$TCMS_PLAN_ID` to point to an existing
            TestPlan where new runs will be added!

            .. warning::

                Does not check if the specified TP exists!

            :return: ``tcms.testplans.models.TestPlan`` PK or 0
            :rtype: int
        """
        return os.environ.get('TCMS_PLAN_ID', 0)

    def default_tester_id(self):
        """
            Used internally and by default this is the user sending the API
            request. Plugins may want to override this.

            :return: User ID
            :rtype: int
        """
        return self.rpc.User.filter()[0]['id']

    def get_plan_id(self, run_id):
        """
            If a TestRun with PK `run_id` exists then return the TestPlan to
            which this TestRun is assigned, otherwise create new TestPlan with
            Product and Version specified by environment variables.

            .. warning::

                For internal use by `.configure()`!

            :param run_id: ``tcms.testruns.models.TestRun`` PK
            :type run_id: int
            :return: ``tcms.testplans.models.TestPlan`` PK
            :rtype: int
        """
        plan_id = self.external_plan_id()
        if plan_id:
            return plan_id

        result = self.rpc.TestRun.filter({'pk': run_id})
        if not result:
            product_id, product_name = self.get_product_id(0)
            version_id, version_name = self.get_version_id(product_id)

            name = f'{self.prefix} Plan for {product_name} ({version_name})'
            result = self.rpc.TestPlan.filter({'name': name,
                                               'product': product_id,
                                               'product_version': version_id})

            if not result:
                plan_type_id = self.get_plan_type_id()

                result = [self.rpc.TestPlan.create({
                    'name': name,
                    'text': 'Created by tcms_api.plugin_helpers.Backend',
                    'product': product_id,
                    'product_version': version_id,
                    'is_active': True,
                    'type': plan_type_id,
                    'author': self.default_tester_id(),
                })]

            # newly created TP
            return result[0]['id']

        # TP to which existing TR is assigned
        return result[0]['plan']

    def get_run_id(self):
        """
            If `$TCMS_RUN_ID` is specified then assume the caller knows
            what they are doing and try to add test results to that TestRun.
            Otherwise will create a TestPlan and TestRun in which to record
            the results!

            .. warning::

                For internal use by `.configure()`!

            :return: ``tcms.testruns.models.TestRun`` PK
            :rtype: int
        """
        run_id = os.environ.get('TCMS_RUN_ID')

        if not run_id:
            product_id, product_name = self.get_product_id(0)
            version_id, version_val = self.get_version_id(product_id)
            build_id, build_number = self.get_build_id(version_id)
            plan_id = self.get_plan_id(0)
            # TR.manager is always the author of the TP, which is either
            # another existing user (existing TP) or self.default_tester_id()
            # in case of newly created TP
            manager_id = self.rpc.TestPlan.filter({
                'pk': plan_id
            })[0]['author']

            testrun = self.rpc.TestRun.create({
                'summary': f'{self.prefix} Results for {product_name}, '
                           f'{version_val}, {build_number}',
                'manager': manager_id,
                'default_tester': self.default_tester_id(),
                'plan': plan_id,
                'build': build_id,
            })
            run_id = testrun['id']

        return int(run_id)

    def finish_test_run(self):
        """
            .. important::

                Test runner plugins **may** call this method!

            May be called at the end when there are no more test executions to
            be sent to Kiwi TCMS. Default implementation will update
            ``TR.stop_date``.

            :return: None
        """
        self.rpc.TestRun.update(self.run_id, {
            'stop_date': datetime.now().isoformat().replace('T', ' ')[:19],
        })

    def test_case_get_or_create(self, summary):
        """
            Search for a TestCase with the specified `summary` and Product.
            If it doesn't exist in the database it will be created!

            .. important::

                Test runner plugins **must** call this method!

            :param summary: A TestCase summary
            :type summary: str
            :return: Serialized ``tcms.testcase.models.TestCase`` and boolean
                     flag to indicate if the TestCase has just been created!
            :rtype: (dict, bool)
        """
        created = False
        test_case = self.rpc.TestCase.filter({
            'summary': summary,
            'category__product': self.product_id,
        })

        if not test_case:
            test_case = [self.rpc.TestCase.create({
                'summary': summary,
                'category': self.category_id,
                'priority': self.priority_id,
                'case_status': self.confirmed_id,
                'notes': 'Created by tcms_api.plugin_helpers.Backend',
                'is_automated': True,
            })]
            created = True

        return test_case[0], created

    def add_test_case_to_plan(self, case_id, plan_id):
        """
            Add a TestCase to a TestPlan if it is not already there!

            .. important::

                Test runner plugins **must** call this method!

            :param case_id: ``tcms.testcases.models.TestCase`` PK
            :type case_id: int
            :param plan_id: ``tcms.testplans.models.TestPlan`` PK
            :type plan_id: int
            :return: None
        """
        if not self.rpc.TestCase.filter({'pk': case_id, 'plan': plan_id}):
            self.rpc.TestPlan.add_case(plan_id, case_id)

    def add_test_case_to_run(self, case_id, run_id):
        """
            Add a TestCase to a TestRun if it is not already there!

            .. important::

                Test runner plugins **must** call this method!

            :param case_id: ``tcms.testcases.models.TestCase`` PK
            :type case_id: int
            :param run_id: ``tcms.testruns.models.TestRun`` PK
            :type run_id: int
            :return: List of serialized ``tcms.testruns.models.TestExecution``
                objects
            :rtype: list(dict)
        """
        result = self.rpc.TestRun.add_case(run_id, case_id)
        if not isinstance(result, list):
            result = [result]
        return result

    def update_test_execution(self,
                              test_execution_id,
                              status_id,
                              comment=None):
        """
            Update TestExecution with a status and comment.

            .. important::

                Test runner plugins **must** call this method!

            :param test_execution_id: ``tcms.testruns.models.TestExecution`` PK
            :type test_execution_id: int
            :param status_id: ``tcms.testruns.models.TestExecutionStatus`` PK,
                              for example the ID for PASSED, FAILED, etc.
            :type status_id: int
            :param comment: the string to add as a comment, defaults to None
            :type comment: str
            :return: None
        """
        self.rpc.TestExecution.update(test_execution_id, {
            'status': status_id,
            'tested_by': self.default_tester_id(),
        })

        if comment:
            self.add_comment(test_execution_id, comment)

    def add_comment(self, test_execution_id, comment):
        """
            Add comment string to TestExecution without changing the status

            .. important::

                Test runner plugins **must** call this method!

            :param test_execution_id: ``tcms.testruns.models.TestExecution`` PK
            :type test_execution_id: int
            :param comment: the string to add as a comment
            :type comment: str
            :return: None
        """
        self.rpc.TestExecution.add_comment(test_execution_id, comment)
