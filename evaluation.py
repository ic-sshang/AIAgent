"""
Evaluation framework for AI Agent responses
Tests accuracy, tool selection, and response quality
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from agent import AIAgent
from database import DatabaseConnection


@dataclass
class TestCase:
    """Represents a single test case"""
    id: str
    question: str
    expected_tools: List[str]  # Tools that should be called
    expected_data_fields: List[str]  # Fields that should be in the response
    validation_query: Optional[str] = None  # SQL to validate against
    expected_behavior: str = "success"  # success, error, clarification
    description: str = ""


@dataclass
class EvaluationResult:
    """Results of a single test case evaluation"""
    test_id: str
    passed: bool
    response: str
    tools_called: List[str]
    tools_correct: bool
    data_fields_found: List[str]
    data_fields_correct: bool
    response_time: float
    error: Optional[str] = None
    notes: str = ""


class AgentEvaluator:
    """Evaluates AI Agent responses for correctness"""
    
    def __init__(self, biller_id: int):
        self.biller_id = biller_id
        self.results: List[EvaluationResult] = []
    
    def run_test_suite(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """
        Run a suite of test cases and return aggregate results.
        
        Args:
            test_cases: List of test cases to run
            
        Returns:
            Dictionary with summary statistics
        """
        print(f"Running {len(test_cases)} test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Testing: {test_case.description or test_case.id}")
            result = self.evaluate_single_case(test_case)
            self.results.append(result)
            
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"  {status} - {result.response_time:.2f}s")
            if not result.passed:
                print(f"  Reason: {result.notes}")
        
        return self.generate_summary()
    
    def evaluate_single_case(self, test_case: TestCase) -> EvaluationResult:
        """
        Evaluate a single test case.
        
        Args:
            test_case: Test case to evaluate
            
        Returns:
            EvaluationResult with detailed results
        """
        start_time = datetime.now()
        tools_called = []
        
        try:
            # Create fresh agent for each test
            agent = AIAgent(self.biller_id)
            agent.add_system_message(
                f"You are a helpful assistant. BillerID is {self.biller_id}. "
                f"Current date is {datetime.now().strftime('%Y-%m-%d')}."
            )
            
            # Capture tool calls by wrapping execute method
            original_execute = agent.tool_registry.execute
            def tracked_execute(tool_name, **kwargs):
                tools_called.append(tool_name)
                return original_execute(tool_name, **kwargs)
            agent.tool_registry.execute = tracked_execute
            
            # Get response
            response = agent.chat(test_case.question)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Validate tools called
            tools_correct = self._validate_tools(tools_called, test_case.expected_tools)
            
            # Validate data fields in response
            data_fields_found = self._extract_data_fields(response, test_case.expected_data_fields)
            data_fields_correct = len(data_fields_found) == len(test_case.expected_data_fields)
            
            # Overall pass/fail
            passed = tools_correct and data_fields_correct
            notes = self._generate_notes(test_case, tools_called, data_fields_found)
            
            # Cleanup
            if hasattr(agent, 'db_connection'):
                agent.db_connection.disconnect()
            
            return EvaluationResult(
                test_id=test_case.id,
                passed=passed,
                response=response,
                tools_called=tools_called,
                tools_correct=tools_correct,
                data_fields_found=data_fields_found,
                data_fields_correct=data_fields_correct,
                response_time=response_time,
                notes=notes
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            return EvaluationResult(
                test_id=test_case.id,
                passed=False,
                response=str(e),
                tools_called=tools_called,
                tools_correct=False,
                data_fields_found=[],
                data_fields_correct=False,
                response_time=response_time,
                error=str(e),
                notes=f"Exception occurred: {str(e)}"
            )
    
    def _validate_tools(self, actual: List[str], expected: List[str]) -> bool:
        """Check if correct tools were called"""
        if not expected:  # No specific tools required
            return True
        
        # Check if all expected tools were called
        return all(tool in actual for tool in expected)
    
    def _extract_data_fields(self, response: str, expected_fields: List[str]) -> List[str]:
        """Extract which expected fields appear in the response"""
        response_lower = response.lower()
        found = []
        
        for field in expected_fields:
            # Check for field name or variations
            if field.lower() in response_lower:
                found.append(field)
        
        return found
    
    def _generate_notes(self, test_case: TestCase, 
                       tools_called: List[str], 
                       data_fields_found: List[str]) -> str:
        """Generate notes about what went wrong"""
        notes = []
        
        if test_case.expected_tools:
            missing_tools = set(test_case.expected_tools) - set(tools_called)
            if missing_tools:
                notes.append(f"Missing tools: {missing_tools}")
            
            extra_tools = set(tools_called) - set(test_case.expected_tools)
            if extra_tools:
                notes.append(f"Unexpected tools: {extra_tools}")
        
        if test_case.expected_data_fields:
            missing_fields = set(test_case.expected_data_fields) - set(data_fields_found)
            if missing_fields:
                notes.append(f"Missing data: {missing_fields}")
        
        return "; ".join(notes) if notes else "All checks passed"
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        avg_time = sum(r.response_time for r in self.results) / total if total > 0 else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "average_response_time": f"{avg_time:.2f}s",
            "results": [
                {
                    "test_id": r.test_id,
                    "passed": r.passed,
                    "tools_called": r.tools_called,
                    "response_time": f"{r.response_time:.2f}s",
                    "notes": r.notes
                }
                for r in self.results
            ]
        }
    
    def export_results(self, filename: str = "evaluation_results.json"):
        """Export results to JSON file"""
        summary = self.generate_summary()
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults exported to {filename}")


# Define test cases
def get_test_cases() -> List[TestCase]:
    """Define standard test cases"""
    return [
        TestCase(
            id="test_001",
            question="I have a customer with account number IVRtest01, how many invoices do they have?",
            expected_tools=["SearchCustomers", "CustomerProfileSummary"],
            expected_data_fields=["invoice", "IVRtest01"],
            description="Multi-step: Search customer then get profile"
        ),
        TestCase(
            id="test_002",
            question="What is the email for customer account IVRtest01?",
            expected_tools=["SearchCustomers"],
            expected_data_fields=["email", "IVRtest01"],
            description="Single-step: Search customer by account"
        ),
        TestCase(
            id="test_003",
            question="Find customers named BRANDY HOLBROOK",
            expected_tools=["SearchCustomers"],
            expected_data_fields=["BRANDY", "HOLBROOK"],
            description="Search by customer name"
        ),
        TestCase(
            id="test_004",
            question="Show me invoices for customer ID 7984",
            expected_tools=["CustomerProfileSummary"],
            expected_data_fields=["invoice", "7984"],
            description="Direct customer ID query"
        ),
        TestCase(
            id="test_005",
            question="Hello, how are you?",
            expected_tools=[],  # Should not call any tools
            expected_data_fields=["hello"],
            description="Conversational - no tool needed"
        ),
    ]


if __name__ == "__main__":
    # Run evaluation
    biller_id = 1537
    evaluator = AgentEvaluator(biller_id)
    
    # Get test cases
    test_cases = get_test_cases()
    
    # Run tests
    summary = evaluator.run_test_suite(test_cases)
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']}")
    print(f"Avg Response Time: {summary['average_response_time']}")
    print("="*60)
    
    # Export results
    evaluator.export_results()
