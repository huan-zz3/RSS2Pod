#!/usr/bin/env python3
"""
English Learning Enhancement Module.

This module provides features to enhance podcast scripts for English learners:
- Vocabulary explanations for difficult words
- Full sentence translations
- Grammar notes
- Pronunciation guides
- Cultural context notes

Designed to work with the script engine to create educational content.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re


class DifficultyLevel(Enum):
    """CEFR difficulty levels for vocabulary."""
    A1 = "A1"  # Beginner
    A2 = "A2"  # Elementary
    B1 = "B1"  # Intermediate
    B2 = "B2"  # Upper Intermediate
    C1 = "C1"  # Advanced
    C2 = "C2"  # Proficient


@dataclass
class VocabularyItem:
    """Represents a vocabulary item with explanations."""
    word: str
    phonetic: str  # IPA pronunciation
    part_of_speech: str
    definition: str
    example_sentence: str
    difficulty: DifficultyLevel
    synonyms: List[str] = field(default_factory=list)
    translations: Dict[str, str] = field(default_factory=dict)  # language -> translation
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "word": self.word,
            "phonetic": self.phonetic,
            "part_of_speech": self.part_of_speech,
            "definition": self.definition,
            "example_sentence": self.example_sentence,
            "difficulty": self.difficulty.value,
            "synonyms": self.synonyms,
            "translations": self.translations,
            "notes": self.notes
        }


@dataclass
class SentenceTranslation:
    """Represents a sentence with translation and notes."""
    original: str
    translation: Dict[str, str]  # language -> translation
    literal_translation: str = ""  # Word-for-word translation
    grammar_notes: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "original": self.original,
            "translation": self.translation,
            "literal_translation": self.literal_translation,
            "grammar_notes": self.grammar_notes,
            "key_phrases": self.key_phrases
        }


@dataclass
class LearningEnhancement:
    """Complete learning enhancement for a script segment."""
    segment_id: str
    vocabulary: List[VocabularyItem] = field(default_factory=list)
    sentence_translations: List[SentenceTranslation] = field(default_factory=list)
    cultural_notes: List[str] = field(default_factory=list)
    comprehension_questions: List[str] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "segment_id": self.segment_id,
            "vocabulary": [v.to_dict() for v in self.vocabulary],
            "sentence_translations": [s.to_dict() for s in self.sentence_translations],
            "cultural_notes": self.cultural_notes,
            "comprehension_questions": self.comprehension_questions,
            "summary": self.summary
        }


class EnglishLearningEnhancer:
    """
    Enhances podcast scripts with English learning features.
    
    This class analyzes script content and adds educational elements
    suitable for English language learners.
    """
    
    def __init__(self, target_language: str = "zh", 
                 difficulty_threshold: DifficultyLevel = DifficultyLevel.B2):
        """
        Initialize the enhancer.
        
        Args:
            target_language: Target language for translations (e.g., 'zh' for Chinese)
            difficulty_threshold: Words at or above this level will be explained
        """
        self.target_language = target_language
        self.difficulty_threshold = difficulty_threshold
        self._vocabulary_cache: Dict[str, VocabularyItem] = {}
    
    def analyze_vocabulary(self, text: str) -> List[VocabularyItem]:
        """
        Analyze text and identify difficult vocabulary.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of VocabularyItem objects for difficult words
        """
        # Extract potential difficult words (simplified implementation)
        # In production, this would use an NLP library and vocabulary database
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        unique_words = set(words)
        
        # Filter out common words (simplified stop word list)
        common_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while', 'about',
            'against', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'what', 'which', 'who', 'whom', 'whose'
        }
        
        difficult_words = unique_words - common_words
        
        # Generate vocabulary items (simplified - would use API in production)
        vocabulary_items = []
        for word in difficult_words:
            if len(word) > 6:  # Simple heuristic for difficult words
                vocab_item = self._create_vocabulary_item(word)
                if vocab_item.difficulty.value >= self.difficulty_threshold.value:
                    vocabulary_items.append(vocab_item)
        
        return vocabulary_items
    
    def _create_vocabulary_item(self, word: str) -> VocabularyItem:
        """
        Create a vocabulary item for a word.
        
        In production, this would call an API or database for accurate information.
        """
        # Placeholder implementation
        return VocabularyItem(
            word=word,
            phonetic=f"/{word}/",  # Would use actual IPA
            part_of_speech="unknown",
            definition=f"Definition of {word}",
            example_sentence=f"Example sentence with {word}",
            difficulty=DifficultyLevel.B2,
            synonyms=[],
            translations={self.target_language: f"{word} 的翻译"},
            notes=""
        )
    
    def translate_sentence(self, sentence: str) -> SentenceTranslation:
        """
        Translate a sentence and add learning notes.
        
        Args:
            sentence: Sentence to translate
            
        Returns:
            SentenceTranslation with translations and notes
        """
        # Placeholder implementation - would use translation API in production
        return SentenceTranslation(
            original=sentence,
            translation={self.target_language: f"[{self.target_language}] {sentence}"},
            literal_translation=sentence,
            grammar_notes=["Grammar notes would appear here"],
            key_phrases=self._extract_key_phrases(sentence)
        )
    
    def _extract_key_phrases(self, sentence: str) -> List[str]:
        """Extract key phrases from a sentence."""
        # Simple extraction - would use NLP in production
        phrases = []
        # Look for common phrase patterns
        patterns = [
            r'\b(in order to|because of|due to|as well as)\b',
            r'\b(on the other hand|in addition|however|therefore)\b',
            r'\b(it is important|it should be|we can see)\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sentence, re.IGNORECASE)
            phrases.extend(matches)
        
        return phrases
    
    def generate_comprehension_questions(self, text: str, count: int = 3) -> List[str]:
        """
        Generate comprehension questions for the text.
        
        Args:
            text: Text to generate questions for
            count: Number of questions to generate
            
        Returns:
            List of comprehension questions
        """
        # Placeholder implementation - would use LLM in production
        questions = [
            "What is the main idea of this passage?",
            "Can you summarize the key points?",
            "What new vocabulary did you learn?",
            "How does this relate to what you already know?"
        ]
        return questions[:count]
    
    def enhance_script_segment(self, segment_id: str, text: str,
                               include_translations: bool = True,
                               include_vocabulary: bool = True,
                               include_questions: bool = True) -> LearningEnhancement:
        """
        Enhance a script segment with learning features.
        
        Args:
            segment_id: Identifier for the segment
            text: Text content to enhance
            include_translations: Whether to include translations
            include_vocabulary: Whether to include vocabulary explanations
            include_questions: Whether to include comprehension questions
            
        Returns:
            LearningEnhancement object with all features
        """
        enhancement = LearningEnhancement(segment_id=segment_id)
        
        if include_vocabulary:
            enhancement.vocabulary = self.analyze_vocabulary(text)
        
        if include_translations:
            # Split into sentences and translate each
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    enhancement.sentence_translations.append(
                        self.translate_sentence(sentence)
                    )
        
        if include_questions:
            enhancement.comprehension_questions = self.generate_comprehension_questions(text)
        
        # Generate summary
        enhancement.summary = self._generate_summary(text)
        
        return enhancement
    
    def _generate_summary(self, text: str) -> str:
        """Generate a brief summary of the text."""
        # Placeholder - would use NLP or LLM in production
        words = text.split()
        if len(words) <= 50:
            return text
        return ' '.join(words[:50]) + "..."
    
    def create_learning_script(self, script_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an entire podcast script with learning features.
        
        Args:
            script_dict: Script dictionary from script_engine
            
        Returns:
            Enhanced script dictionary with learning features
        """
        enhanced_script = script_dict.copy()
        enhanced_script['learning_enhancements'] = []
        
        # Process each segment
        for i, segment in enumerate(script_dict.get('segments', [])):
            # Extract text from segment
            segment_text = self._extract_text_from_segment(segment)
            
            if segment_text:
                enhancement = self.enhance_script_segment(
                    segment_id=f"segment_{i}",
                    text=segment_text
                )
                enhanced_script['learning_enhancements'].append(enhancement.to_dict())
        
        return enhanced_script
    
    def _extract_text_from_segment(self, segment: Dict[str, Any]) -> str:
        """Extract text content from a segment dictionary."""
        # Handle different segment formats
        if 'line' in segment:
            return segment['line']
        elif 'content' in segment:
            return segment['content']
        elif 'speakers' in segment:
            # Combine all speaker lines
            texts = []
            for speaker in segment.get('speakers', []):
                if isinstance(speaker, dict):
                    if 'lines' in speaker:
                        texts.extend(speaker['lines'])
                    elif 'line' in speaker:
                        texts.append(speaker['line'])
            return ' '.join(texts)
        return ""


def create_vocabulary_list(vocabulary_items: List[VocabularyItem],
                           format: str = "markdown") -> str:
    """
    Create a formatted vocabulary list from vocabulary items.
    
    Args:
        vocabulary_items: List of VocabularyItem objects
        format: Output format (markdown, html, plain)
        
    Returns:
        Formatted vocabulary list as string
    """
    if format == "markdown":
        output = ["## Vocabulary List\n"]
        for item in vocabulary_items:
            output.append(f"### {item.word}")
            output.append(f"- **Pronunciation:** {item.phonetic}")
            output.append(f"- **Part of Speech:** {item.part_of_speech}")
            output.append(f"- **Definition:** {item.definition}")
            output.append(f"- **Difficulty:** {item.difficulty.value}")
            output.append(f"- **Example:** {item.example_sentence}")
            if item.synonyms:
                output.append(f"- **Synonyms:** {', '.join(item.synonyms)}")
            if item.translations:
                for lang, trans in item.translations.items():
                    output.append(f"- **Translation ({lang}):** {trans}")
            output.append("")
        return '\n'.join(output)
    
    elif format == "plain":
        output = ["VOCABULARY LIST\n"]
        for item in vocabulary_items:
            output.append(f"{item.word.upper()}")
            output.append(f"  Pronunciation: {item.phonetic}")
            output.append(f"  Definition: {item.definition}")
            output.append(f"  Example: {item.example_sentence}")
            output.append("")
        return '\n'.join(output)
    
    else:
        raise ValueError(f"Unsupported format: {format}")


def create_study_guide(enhancement: LearningEnhancement,
                       format: str = "markdown") -> str:
    """
    Create a study guide from a learning enhancement.
    
    Args:
        enhancement: LearningEnhancement object
        format: Output format
        
    Returns:
        Formatted study guide
    """
    if format == "markdown":
        output = [f"# Study Guide: {enhancement.segment_id}\n"]
        
        # Summary
        output.append("## Summary\n")
        output.append(enhancement.summary)
        output.append("")
        
        # Vocabulary
        if enhancement.vocabulary:
            output.append("## New Vocabulary\n")
            for vocab in enhancement.vocabulary:
                output.append(f"- **{vocab.word}** ({vocab.phonetic}): {vocab.definition}")
            output.append("")
        
        # Key Sentences
        if enhancement.sentence_translations:
            output.append("## Key Sentences\n")
            for sent in enhancement.sentence_translations[:5]:  # Limit to 5
                output.append(f"- {sent.original}")
                if sent.translation:
                    for lang, trans in sent.translation.items():
                        output.append(f"  - {lang}: {trans}")
            output.append("")
        
        # Comprehension Questions
        if enhancement.comprehension_questions:
            output.append("## Comprehension Questions\n")
            for i, question in enumerate(enhancement.comprehension_questions, 1):
                output.append(f"{i}. {question}")
            output.append("")
        
        return '\n'.join(output)
    
    else:
        raise ValueError(f"Unsupported format: {format}")


# Example usage and testing
if __name__ == "__main__":
    # Create enhancer
    enhancer = EnglishLearningEnhancer(target_language="zh")
    
    # Sample text
    sample_text = """
    The future of artificial intelligence in healthcare is promising. 
    Machine learning algorithms can analyze medical images with remarkable accuracy.
    Furthermore, personalized treatment plans are becoming more sophisticated.
    """
    
    # Analyze vocabulary
    print("=== Vocabulary Analysis ===")
    vocab_items = enhancer.analyze_vocabulary(sample_text)
    for item in vocab_items:
        print(f"  - {item.word}: {item.definition}")
    
    # Enhance segment
    print("\n=== Learning Enhancement ===")
    enhancement = enhancer.enhance_script_segment(
        segment_id="sample_001",
        text=sample_text
    )
    
    print(f"Segment: {enhancement.segment_id}")
    print(f"Vocabulary items: {len(enhancement.vocabulary)}")
    print(f"Sentences translated: {len(enhancement.sentence_translations)}")
    print(f"Questions: {len(enhancement.comprehension_questions)}")
    print(f"Summary: {enhancement.summary[:100]}...")
    
    # Create study guide
    print("\n=== Study Guide ===")
    study_guide = create_study_guide(enhancement)
    print(study_guide[:500])
    
    # Create vocabulary list
    print("\n=== Vocabulary List ===")
    vocab_list = create_vocabulary_list(vocab_items)
    print(vocab_list[:500])
