"""Export modules for reports and analysis."""

from .pdf_generator import PDFGenerator

def generate_roi_report(simulation_id: str, user_email: str, results: dict, agent_stats: list):
    """Generate PDF report for simulation."""
    gen = PDFGenerator()
    return gen.generate_report(simulation_id, user_email, results, agent_stats)

__all__ = ["generate_roi_report", "PDFGenerator"]
