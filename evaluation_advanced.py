"""
Advanced evaluation metrics for AI Agent
Includes accuracy, precision, recall, and regression testing
"""

import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from agent import AIAgent
from database import DatabaseConnection


@dataclass
class GroundTruthTestCase:
    """Test case with known correct answer from database"""
    id: str
    question: str
    ground_truth_query: str  # SQL to get the correct answer
    response_parser: callable  # Function to extract answer from agent response
    description: str = ""


class AdvancedEvaluator:
    """Advanced evaluation comparing agent responses to ground truth"""
    
    def __init__(self, biller_id: int):
        self.biller_id = biller_id
        self.db = DatabaseConnection(biller_id)
        self.db.connect()
    
    def __del__(self):
        if self.db:
            self.db.disconnect()
    
    def evaluate_accuracy(self, test_cases: List[GroundTruthTestCase]) -> Dict[str, Any]:
        """
        Evaluate accuracy by comparing agent responses to ground truth.
        
        Returns:
            Dictionary with accuracy metrics
        """
        results = []
        correct = 0
        
        for test_case in test_cases:
            # Get ground truth from database
            ground_truth = self._get_ground_truth(test_case.ground_truth_query)
            
            # Get agent response
            agent = AIAgent(self.biller_id)
            agent.add_system_message(f"BillerID is {self.biller_id}.")
            response = agent.chat(test_case.question)
            
            # Parse agent response
            parsed_response = test_case.response_parser(response)
            
            # Compare
            is_correct = self._compare_values(ground_truth, parsed_response)
            if is_correct:
                correct += 1
            
            results.append({
                "test_id": test_case.id,
                "question": test_case.question,
                "ground_truth": str(ground_truth),
                "agent_response": str(parsed_response),
                "correct": is_correct
            })
            
            # Cleanup
            if hasattr(agent, 'db_connection'):
                agent.db_connection.disconnect()
        
        accuracy = correct / len(test_cases) if test_cases else 0
        
        return {
            "accuracy": f"{accuracy * 100:.2f}%",
            "correct": correct,
            "total": len(test_cases),
            "details": results
        }
    
    def _get_ground_truth(self, query: str) -> Any:
        """Execute query to get ground truth"""
        results = self.db.execute_query(query)
        if results and len(results) > 0:
            return results[0][0] if len(results[0]) == 1 else results[0]
        return None
    
    def _compare_values(self, ground_truth: Any, parsed: Any) -> bool:
        """Compare ground truth with parsed response"""
        if ground_truth is None or parsed is None:
            return False
        
        # Convert to strings and normalize
        gt_str = str(ground_truth).strip().lower()
        parsed_str = str(parsed).strip().lower()
        
        return gt_str == parsed_str or gt_str in parsed_str
    
    def regression_test(self, baseline_file: str) -> Dict[str, Any]:
        """
        Compare current responses against baseline.
        
        Args:
            baseline_file: JSON file with baseline responses
            
        Returns:
            Regression test results
        """
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        regressions = []
        improvements = []
        unchanged = 0
        
        for test in baseline.get('results', []):
            test_id = test['test_id']
            baseline_passed = test['passed']
            
            # Re-run test (you'd need to store original test cases)
            # This is a simplified example
            current_passed = True  # Would actually re-run
            
            if baseline_passed and not current_passed:
                regressions.append(test_id)
            elif not baseline_passed and current_passed:
                improvements.append(test_id)
            else:
                unchanged += 1
        
        return {
            "regressions": len(regressions),
            "improvements": len(improvements),
            "unchanged": unchanged,
            "regression_tests": regressions,
            "improved_tests": improvements
        }


# Example parsers for extracting specific values from responses
def parse_count(response: str) -> int:
    """Extract a count/number from response"""
    import re
    numbers = re.findall(r'\b\d+\b', response)
    return int(numbers[0]) if numbers else 0


def parse_email(response: str) -> str:
    """Extract email from response"""
    import re
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', response)
    return emails[0] if emails else ""


def parse_yes_no(response: str) -> bool:
    """Extract yes/no answer"""
    response_lower = response.lower()
    return "yes" in response_lower or "true" in response_lower


# Example ground truth test cases
def get_ground_truth_tests() -> List[GroundTruthTestCase]:
    """Define tests with ground truth validation"""
    return [
        GroundTruthTestCase(
            id="gt_001",
            question="How many invoices does customer ID 7984 have?",
            ground_truth_query="EXEC dbo.selCustomerProfileSummary @CustomerID = 7984",
            response_parser=parse_count,
            description="Validate invoice count matches database"
        ),
        # Add more ground truth tests...
    ]


if __name__ == "__main__":
    biller_id = 1537
    
    print("Running Advanced Evaluation...")
    evaluator = AdvancedEvaluator(biller_id)
    
    # Accuracy test
    test_cases = get_ground_truth_tests()
    accuracy_results = evaluator.evaluate_accuracy(test_cases)
    
    print("\nACCURACY RESULTS")
    print("="*60)
    print(f"Accuracy: {accuracy_results['accuracy']}")
    print(f"Correct: {accuracy_results['correct']}/{accuracy_results['total']}")
    
    # Save results
    with open("accuracy_results.json", 'w') as f:
        json.dump(accuracy_results, f, indent=2)
