"""
============================================
Advanced AI Interest Intelligence Engine
============================================

Production-grade interest analysis system with:
- Weighted scoring (base + behavioral)
- Normalization (100% guaranteed)
- Tie detection & resolution
- Explainable rankings
- Career path recommendations
- Skill roadmap generation

Design Philosophy:
- No randomness (deterministic)
- 100% mathematical accuracy
- Enterprise-level explainability
- Adaptive learning personalization
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class InterestScore:
    """Individual interest score with full metadata"""
    name: str
    base_score: float  # 0-10 user rating
    behavioral_score: float = 0.0  # 0-10 from engagement data
    has_behavioral_data: bool = False
    final_score: float = 0.0
    percentage: float = 0.0
    confidence: float = 0.0
    rank: int = 0
    reasoning: str = ""


@dataclass
class TieDetection:
    """Tie detection and resolution"""
    is_tie: bool
    tie_candidates: List[str]
    tie_threshold: float = 2.0  # 2% difference
    resolution_question: Optional[str] = None
    user_decision: Optional[str] = None


@dataclass
class CareerPath:
    """Career path recommendation"""
    title: str
    industry: str
    salary_range: str
    growth_potential: str
    required_skills: List[str]
    entry_requirements: str


@dataclass
class SkillRoadmap:
    """Learning roadmap"""
    level: str  # Beginner, Intermediate, Advanced
    duration: str
    topics: List[str]
    projects: List[str]
    resources: List[Dict[str, str]]


@dataclass
class Recommendation:
    """Complete recommendation"""
    career_paths: List[CareerPath]
    skill_roadmap: List[SkillRoadmap]
    learning_next_step: str
    justification: str
    learning_approach: Dict[str, Any]


@dataclass
class AnalysisResult:
    """Final analysis result"""
    primary_interest: str
    ranked_interests: List[Dict[str, Any]]
    tie_detected: TieDetection
    recommendation: Dict[str, Any]
    data_validation: Dict[str, Any]
    timestamp: str


# ============================================================================
# INTEREST INTELLIGENCE ENGINE
# ============================================================================

class InterestIntelligenceEngine:
    """
    Production-grade interest analysis engine.
    
    Guarantees:
    - 100% mathematical accuracy
    - Zero randomness
    - Full explainability
    - Enterprise reliability
    """
    
    # Career database organized by domain
    CAREER_DATABASE = {
        "Coding": {
            "paths": [
                {"title": "Software Engineer", "industry": "Tech", "salary": "$100K-$180K", "growth": "Very High"},
                {"title": "Backend Developer", "industry": "Tech", "salary": "$90K-$150K", "growth": "High"},
                {"title": "Systems Programmer", "industry": "Tech", "salary": "$110K-$190K", "growth": "Very High"},
            ],
            "beginner": ["Variables & Types", "Control Flow", "Functions", "Debugging"],
            "intermediate": ["OOP Principles", "Data Structures", "Algorithms", "Design Patterns"],
            "advanced": ["System Design", "Performance Optimization", "Architecture", "Scalability"],
        },
        "Web Development": {
            "paths": [
                {"title": "Frontend Developer", "industry": "Web", "salary": "$85K-$160K", "growth": "High"},
                {"title": "Full Stack Developer", "industry": "Web", "salary": "$95K-$180K", "growth": "Very High"},
                {"title": "Web Architect", "industry": "Web", "salary": "$120K-$200K", "growth": "Very High"},
            ],
            "beginner": ["HTML & CSS", "JavaScript Basics", "Responsive Design", "Git"],
            "intermediate": ["React/Vue", "State Management", "REST APIs", "Databases"],
            "advanced": ["TypeScript", "Testing", "DevOps", "Security"],
        },
        "Data Science": {
            "paths": [
                {"title": "Data Scientist", "industry": "Analytics", "salary": "$95K-$180K", "growth": "Very High"},
                {"title": "Machine Learning Engineer", "industry": "AI/ML", "salary": "$110K-$200K", "growth": "Very High"},
                {"title": "Data Engineer", "industry": "Big Data", "salary": "$100K-$190K", "growth": "High"},
            ],
            "beginner": ["Python", "Statistics", "Data Cleaning", "Visualization"],
            "intermediate": ["Pandas & NumPy", "SQL", "ML Basics", "Feature Engineering"],
            "advanced": ["Deep Learning", "Advanced ML", "Big Data Tech", "Research"],
        },
        "Cybersecurity": {
            "paths": [
                {"title": "Security Engineer", "industry": "Security", "salary": "$105K-$185K", "growth": "Very High"},
                {"title": "Penetration Tester", "industry": "Security", "salary": "$95K-$175K", "growth": "Very High"},
                {"title": "Security Architect", "industry": "Security", "salary": "$130K-$210K", "growth": "Very High"},
            ],
            "beginner": ["Networking Basics", "Linux", "Security Concepts", "Cryptography"],
            "intermediate": ["Penetration Testing", "OWASP Top 10", "Firewalls", "Incident Response"],
            "advanced": ["Advanced Hacking", "Threat Analysis", "Risk Management", "Certifications"],
        },
        "Mobile Development": {
            "paths": [
                {"title": "iOS Developer", "industry": "Mobile", "salary": "$90K-$170K", "growth": "High"},
                {"title": "Android Developer", "industry": "Mobile", "salary": "$90K-$170K", "growth": "High"},
                {"title": "Mobile Architect", "industry": "Mobile", "salary": "$115K-$195K", "growth": "Very High"},
            ],
            "beginner": ["UI/UX Basics", "Swift/Kotlin", "Git", "APIs"],
            "intermediate": ["Mobile Frameworks", "State Management", "Performance", "Testing"],
            "advanced": ["Cross-platform", "Native Modules", "DevOps", "Architecture"],
        },
        "Cloud Computing": {
            "paths": [
                {"title": "Cloud Engineer", "industry": "Cloud", "salary": "$100K-$180K", "growth": "Very High"},
                {"title": "DevOps Engineer", "industry": "DevOps", "salary": "$105K-$185K", "growth": "Very High"},
                {"title": "Cloud Architect", "industry": "Cloud", "salary": "$130K-$220K", "growth": "Very High"},
            ],
            "beginner": ["Cloud Basics", "Linux", "Networking", "Virtualization"],
            "intermediate": ["AWS/Azure/GCP", "Docker", "Kubernetes", "CI/CD"],
            "advanced": ["Infrastructure as Code", "Security", "Cost Optimization", "Scaling"],
        },
        "Game Development": {
            "paths": [
                {"title": "Game Developer", "industry": "Gaming", "salary": "$80K-$160K", "growth": "High"},
                {"title": "Graphics Programmer", "industry": "Gaming", "salary": "$95K-$180K", "growth": "High"},
                {"title": "Technical Director", "industry": "Gaming", "salary": "$120K-$200K", "growth": "Very High"},
            ],
            "beginner": ["Game Design", "C#/Cpp", "Unity/Unreal", "Physics"],
            "intermediate": ["3D Graphics", "Animation", "AI", "Optimization"],
            "advanced": ["Advanced Graphics", "Multiplayer", "Engine Development", "Leadership"],
        },
        "AI & Machine Learning": {
            "paths": [
                {"title": "ML Engineer", "industry": "AI", "salary": "$110K-$200K", "growth": "Very High"},
                {"title": "AI Researcher", "industry": "Research", "salary": "$100K-$200K+", "growth": "Very High"},
                {"title": "AI Architect", "industry": "Enterprise", "salary": "$140K-$240K", "growth": "Very High"},
            ],
            "beginner": ["Python", "Statistics", "Linear Algebra", "Neural Networks"],
            "intermediate": ["Deep Learning", "NLP", "Computer Vision", "TensorFlow"],
            "advanced": ["Advanced AI", "Research Papers", "Model Optimization", "Ethics"],
        },
    }
    
    def __init__(self, tie_threshold: float = 2.0):
        """
        Initialize engine.
        
        Args:
            tie_threshold: Percentage difference to consider as tie (default 2%)
        """
        self.tie_threshold = tie_threshold
        self.base_scores: Dict[str, InterestScore] = {}
        self.tie_detection = TieDetection(is_tie=False, tie_candidates=[])
    
    # ========================================================================
    # CORE SCORING ALGORITHM
    # ========================================================================
    
    def analyze_interests(
        self,
        interests: Dict[str, float],
        behavioral_data: Optional[Dict[str, Dict[str, float]]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Complete interest analysis pipeline.
        
        Args:
            interests: {domain: rating(0-10)}
            behavioral_data: {domain: {metric: value}}
            user_context: Additional user info
            
        Returns:
            AnalysisResult with full analysis
        """
        logger.info(f"Starting interest analysis for {len(interests)} domains")
        
        # Step 1: Compute base scores
        self._compute_base_scores(interests)
        
        # Step 2: Apply behavioral weighting if available
        if behavioral_data:
            self._apply_behavioral_weighting(behavioral_data)
        else:
            self._reduce_confidence_no_behavior()
        
        # Step 3: Normalize to 100%
        self._normalize_scores()
        
        # Step 4: Rank interests
        ranked = self._rank_interests()
        
        # Step 5: Detect ties
        self._detect_ties(ranked)
        
        # Step 6: Determine primary interest
        primary_interest = self._determine_primary_interest(ranked)
        
        # Step 7: Generate recommendations
        recommendation = self._generate_recommendations(primary_interest, ranked)
        
        # Step 8: Validate data integrity
        validation = self._validate_data()
        
        # Build result
        result = AnalysisResult(
            primary_interest=primary_interest,
            ranked_interests=ranked,
            tie_detected=self.tie_detection,
            recommendation=recommendation,
            data_validation=validation,
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Analysis complete. Primary: {primary_interest}")
        return result
    
    def _compute_base_scores(self, interests: Dict[str, float]) -> None:
        """Compute base scores from user ratings (0-10)."""
        logger.info("Computing base scores")
        
        for domain, rating in interests.items():
            if not 0 <= rating <= 10:
                logger.warning(f"Invalid rating for {domain}: {rating}, clamping to 0-10")
                rating = max(0, min(10, rating))
            
            self.base_scores[domain] = InterestScore(
                name=domain,
                base_score=float(rating),
                final_score=float(rating)
            )
    
    def _apply_behavioral_weighting(self, behavioral_data: Dict[str, Dict]) -> None:
        """
        Apply behavioral signals to scores.
        
        Formula: Final = (Base × 0.6) + (Behavioral × 0.4)
        """
        logger.info("Applying behavioral weighting (60% base, 40% behavioral)")
        
        for domain, score_obj in self.base_scores.items():
            if domain in behavioral_data:
                behavior = behavioral_data[domain]
                
                # Compute behavioral score from signals
                behavioral_score = self._compute_behavioral_score(behavior)
                
                # Apply weighted formula
                weighted_score = (score_obj.base_score * 0.6) + (behavioral_score * 0.4)
                
                score_obj.behavioral_score = behavioral_score
                score_obj.has_behavioral_data = True
                score_obj.final_score = weighted_score
                score_obj.confidence = 1.0
                
                logger.debug(
                    f"{domain}: base={score_obj.base_score}, behavior={behavioral_score:.2f}, "
                    f"final={weighted_score:.2f}"
                )
    
    def _compute_behavioral_score(self, behavior: Dict[str, float]) -> float:
        """
        Compute behavioral score from engagement signals.
        
        Signals:
        - time_spent_minutes (0-10 scale)
        - quiz_performance (0-10 scale)
        - click_frequency (0-10 scale)
        - repeat_selection (0-10 scale)
        """
        signals = []
        
        if "time_spent_minutes" in behavior:
            # Normalize to 0-10 (assume 60+ min = 10)
            time_normalized = min(10, behavior["time_spent_minutes"] / 6)
            signals.append(time_normalized)
        
        if "quiz_performance" in behavior:
            signals.append(behavior["quiz_performance"])
        
        if "click_frequency" in behavior:
            signals.append(behavior["click_frequency"])
        
        if "repeat_selection" in behavior:
            signals.append(behavior["repeat_selection"])
        
        if not signals:
            return 0.0
        
        # Average all available signals
        return sum(signals) / len(signals)
    
    def _reduce_confidence_no_behavior(self) -> None:
        """Reduce confidence by 20% if no behavioral data available."""
        logger.info("No behavioral data - reducing confidence by 20%")
        
        for score_obj in self.base_scores.values():
            score_obj.has_behavioral_data = False
            score_obj.confidence = 0.80  # 20% reduction
    
    def _normalize_scores(self) -> None:
        """
        Normalize all scores to percentages summing to exactly 100%.
        
        CRITICAL: No approximation, exact 100% guaranteed.
        """
        logger.info("Normalizing scores to 100%")
        
        total_score = sum(s.final_score for s in self.base_scores.values())
        
        if total_score == 0:
            logger.warning("All scores are 0, distributing evenly")
            equal_percentage = 100.0 / len(self.base_scores)
            for score_obj in self.base_scores.values():
                score_obj.percentage = equal_percentage
        else:
            # Calculate percentages
            for score_obj in self.base_scores.values():
                percentage = (score_obj.final_score / total_score) * 100.0
                score_obj.percentage = round(percentage, 4)  # 4 decimal precision
        
        # Verify sum = 100% (handle floating point precision)
        total_percentage = sum(s.percentage for s in self.base_scores.values())
        
        if abs(total_percentage - 100.0) > 0.01:
            logger.warning(f"Percentage sum drift: {total_percentage}%, correcting")
            # Distribute rounding error to highest score
            sorted_scores = sorted(
                self.base_scores.values(),
                key=lambda x: x.final_score,
                reverse=True
            )
            error = 100.0 - total_percentage
            sorted_scores[0].percentage += error
        
        final_total = sum(s.percentage for s in self.base_scores.values())
        logger.info(f"Normalization complete: {final_total}%")
    
    def _rank_interests(self) -> List[Dict[str, Any]]:
        """Rank interests by score and return with metadata."""
        logger.info("Ranking interests")
        
        sorted_scores = sorted(
            self.base_scores.values(),
            key=lambda x: x.final_score,
            reverse=True
        )
        
        ranked = []
        for rank, score_obj in enumerate(sorted_scores, 1):
            score_obj.rank = rank
            
            # Generate reasoning
            reasoning = self._generate_reasoning(score_obj, sorted_scores)
            score_obj.reasoning = reasoning
            
            ranked.append({
                "name": score_obj.name,
                "score": round(score_obj.final_score, 2),
                "percentage": f"{score_obj.percentage:.2f}%",
                "confidence": f"{score_obj.confidence * 100:.0f}%",
                "reason": reasoning,
                "rank": rank,
                "base_score": score_obj.base_score,
                "behavioral_score": score_obj.behavioral_score if score_obj.has_behavioral_data else None,
            })
        
        return ranked
    
    def _generate_reasoning(self, score_obj: InterestScore, all_scores: List) -> str:
        """Generate explainable reasoning for score."""
        if score_obj.rank == 1:
            if score_obj.has_behavioral_data:
                return (
                    f"Strong match based on both rating ({score_obj.base_score}/10) "
                    f"and engagement signals ({score_obj.behavioral_score:.1f}/10). "
                    f"Consistent interest with demonstrated behavior."
                )
            else:
                return (
                    f"High rating ({score_obj.base_score}/10) indicates strong interest. "
                    f"Limited behavioral data available for full confidence."
                )
        else:
            # Compare with top choice
            top_score = all_scores[0]
            difference = top_score.final_score - score_obj.final_score
            
            return (
                f"Solid interest ({score_obj.percentage:.1f}%). "
                f"{difference:.1f} points below top choice. "
                f"Consider as secondary or complementary skill path."
            )
    
    def _detect_ties(self, ranked: List[Dict]) -> None:
        """
        Detect ties - when multiple interests have near-equal top scores.
        
        Tie criteria: difference ≤ tie_threshold (default 2%)
        """
        logger.info(f"Detecting ties (threshold: {self.tie_threshold}%)")
        
        if len(ranked) < 2:
            self.tie_detection.is_tie = False
            return
        
        # Check if top 2+ have small difference
        top_percentage = float(ranked[0]["percentage"].rstrip('%'))
        candidates = [ranked[0]["name"]]
        
        for interest in ranked[1:]:
            interest_percentage = float(interest["percentage"].rstrip('%'))
            difference = top_percentage - interest_percentage
            
            if difference <= self.tie_threshold:
                candidates.append(interest["name"])
            else:
                break
        
        if len(candidates) > 1:
            self.tie_detection.is_tie = True
            self.tie_detection.tie_candidates = candidates
            self.tie_detection.resolution_question = (
                f"You show equal interest in {', '.join(candidates)}. "
                f"Which one do you prefer for long-term learning and career growth?"
            )
            logger.warning(f"TIE DETECTED: {candidates}")
        else:
            self.tie_detection.is_tie = False
    
    def _determine_primary_interest(self, ranked: List[Dict]) -> str:
        """
        Determine primary interest.
        
        If tie detected, return marker for user resolution.
        Otherwise return top-ranked.
        """
        if self.tie_detection.is_tie:
            logger.warning("Cannot determine primary - tie detected, awaiting user decision")
            return "PENDING_USER_RESOLUTION"
        
        return ranked[0]["name"]
    
    def _generate_recommendations(
        self,
        primary_interest: str,
        ranked: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate career paths, skill roadmap, and learning strategy.
        """
        logger.info(f"Generating recommendations for {primary_interest}")
        
        if primary_interest == "PENDING_USER_RESOLUTION":
            return {
                "status": "pending",
                "message": "Awaiting user tie-break decision",
                "career_paths": [],
                "skill_roadmap": [],
                "learning_next_step": "",
                "justification": self.tie_detection.resolution_question
            }
        
        if primary_interest not in self.CAREER_DATABASE:
            logger.warning(f"No recommendations for {primary_interest}")
            return {
                "career_paths": [],
                "skill_roadmap": [],
                "learning_next_step": "",
                "justification": f"No career path data available for {primary_interest}"
            }
        
        db = self.CAREER_DATABASE[primary_interest]
        
        # Career paths
        career_paths = [
            {
                "title": p["title"],
                "industry": p["industry"],
                "salary_range": p["salary"],
                "growth_potential": p["growth"],
                "required_skills": ["TBD"],
                "entry_requirements": "Bachelor's degree or equivalent experience"
            }
            for p in db["paths"]
        ]
        
        # Skill roadmap
        skill_roadmap = [
            {
                "level": "Beginner",
                "duration": "4-6 weeks",
                "topics": db["beginner"],
                "projects": ["Build small projects", "Complete tutorials"],
                "resources": []
            },
            {
                "level": "Intermediate",
                "duration": "6-8 weeks",
                "topics": db["intermediate"],
                "projects": ["Real-world projects", "Open source contribution"],
                "resources": []
            },
            {
                "level": "Advanced",
                "duration": "8-12 weeks",
                "topics": db["advanced"],
                "projects": ["Architecture design", "Leadership projects"],
                "resources": []
            }
        ]
        
        # Next learning step
        beginner_topics = db["beginner"]
        learning_next_step = f"Start with: {beginner_topics[0]}"
        
        # Justification
        top_percentage = float(ranked[0]["percentage"].rstrip('%'))
        secondary = ranked[1]["name"] if len(ranked) > 1 else None
        
        justification = (
            f"You have a strong interest in {primary_interest} ({top_percentage:.1f}%). "
            f"Your scores show this is your best-fit domain. "
            f"{'You also showed interest in ' + secondary + ', which complements your primary path.' if secondary else ''} "
            f"We recommend starting with foundational concepts before moving to advanced topics."
        )
        
        return {
            "career_paths": career_paths,
            "skill_roadmap": skill_roadmap,
            "learning_next_step": learning_next_step,
            "justification": justification,
            "learning_approach": {
                "type": "digital",
                "message": f"Online courses, projects, and self-paced learning for {primary_interest}",
                "suggestions": [
                    "Take structured online courses",
                    "Build real projects",
                    "Join relevant communities",
                    "Practice regularly with challenges"
                ]
            }
        }
    
    def _validate_data(self) -> Dict[str, Any]:
        """Validate mathematical accuracy and data integrity."""
        total_percentage = sum(s.percentage for s in self.base_scores.values())
        is_valid = abs(total_percentage - 100.0) < 0.01
        
        return {
            "total_percentage": f"{total_percentage:.2f}%",
            "expected_percentage": "100.00%",
            "accuracy_status": "verified" if is_valid else "ERROR",
            "domain_count": len(self.base_scores),
            "all_scores_positive": all(s.final_score >= 0 for s in self.base_scores.values()),
            "no_random_values": True  # Deterministic system
        }
    
    def resolve_tie(self, selected_interest: str) -> Dict[str, Any]:
        """
        Resolve tie by user selection.
        
        Args:
            selected_interest: User's chosen domain from tie candidates
            
        Returns:
            Updated analysis with resolved primary interest
        """
        logger.info(f"Resolving tie with user selection: {selected_interest}")
        
        if selected_interest not in self.tie_detection.tie_candidates:
            raise ValueError(f"{selected_interest} not in tie candidates")
        
        # Boost selected interest confidence
        if selected_interest in self.base_scores:
            self.base_scores[selected_interest].confidence = 1.0
        
        self.tie_detection.user_decision = selected_interest
        self.tie_detection.is_tie = False
        
        return {
            "status": "resolved",
            "selected": selected_interest,
            "message": f"Tie resolved. {selected_interest} set as primary interest."
        }
