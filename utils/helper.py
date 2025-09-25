from datetime import datetime, timedelta

# I ask Google Gemini for help in coding this
def get_week_boundaries(date_obj: datetime):
    """Get the date for start of week and end of week

    Args:
        date_obj (datetime): Will use datetime.now() here
    """
    start_of_week = date_obj - timedelta(days=date_obj.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)
    
    return start_of_week, end_of_week