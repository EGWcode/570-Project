'''
 reviews.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all review and feedback related database queries for the
 FLOW system. It provides functions for submitting, retrieving, and analyzing
 customer reviews across all branches. It is used by the customer interface
 for submitting feedback and the manager interface for viewing and analyzing customer sentiment.

 Functions:
   - submit_review()              : submits a new customer review for a branch
   - get_reviews_by_branch()      : retrieves all reviews for a specific branch
   - get_reviews_by_customer()    : retrieves all reviews submitted by a customer
   - get_average_rating()         : calculates the average rating for a branch
   - get_recent_reviews()         : retrieves the most recent reviews for a branch
   - get_review_by_id()           : retrieves a single review by review_id
   - update_sentiment_score()     : updates the sentiment score for a review
   - get_sentiment_summary()      : retrieves average sentiment score for a branch
   - get_rating_breakdown()       : retrieves count of each rating for a branch
'''

from config.db_config import get_connection, close_connection

def submit_review(person_id, branch_id, rating, comments=None):
    """
    Submits a new customer review for a branch.
    Sentiment score is null by default and can be updated
    later by the analytics system using update_sentiment_score().
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO review (person_id, branch_id, rating, comments)
            VALUES (%s, %s, %s, %s)
        """, (person_id, branch_id, rating, comments))

        conn.commit()

        try:
            from config.mongo_config import log_review
            log_review(person_id, branch_id, rating, comments)
        except Exception:
            pass

        return True, "Review submitted successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Review submission failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_reviews_by_branch(branch_id):
    """Retrieves all reviews for a specific branch ordered by most recent."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.review_id, r.rating, r.comments,
                   r.sentiment_score, r.created_at,
                   p.first_name, p.last_name
            FROM review r
            JOIN person p ON r.person_id = p.person_id
            WHERE r.branch_id = %s
            ORDER BY r.created_at DESC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving reviews by branch: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_reviews_by_customer(person_id):
    """Retrieves all reviews submitted by a specific customer."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.review_id, r.rating, r.comments,
                   r.sentiment_score, r.created_at,
                   b.branch_name
            FROM review r
            JOIN branch b ON r.branch_id = b.branch_id
            WHERE r.person_id = %s
            ORDER BY r.created_at DESC
        """, (person_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving reviews by customer: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_average_rating(branch_id):
    """Calculates the average rating for a specific branch."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                COUNT(review_id) as total_reviews,
                ROUND(AVG(rating), 2) as average_rating
            FROM review
            WHERE branch_id = %s
        """, (branch_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error calculating average rating: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_recent_reviews(branch_id, limit=10):
    """Retrieves the most recent reviews for a branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.review_id, r.rating, r.comments,
                   r.sentiment_score, r.created_at,
                   p.first_name, p.last_name
            FROM review r
            JOIN person p ON r.person_id = p.person_id
            WHERE r.branch_id = %s
            ORDER BY r.created_at DESC
            LIMIT %s
        """, (branch_id, limit))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving recent reviews: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_review_by_id(review_id):
    """Retrieves a single review by review_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.review_id, r.rating, r.comments,
                   r.sentiment_score, r.created_at,
                   p.first_name, p.last_name,
                   b.branch_name
            FROM review r
            JOIN person p ON r.person_id = p.person_id
            JOIN branch b ON r.branch_id = b.branch_id
            WHERE r.review_id = %s
        """, (review_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving review: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def update_sentiment_score(review_id, sentiment_score):
    """Updates the sentiment score for a review."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE review
            SET sentiment_score = %s
            WHERE review_id = %s
        """, (sentiment_score, review_id))

        if cursor.rowcount == 0:
            return False, "Review not found."

        conn.commit()
        return True, "Sentiment score updated successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Sentiment score update failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_sentiment_summary(branch_id):
    """Retrieves average sentiment score and review count for a branch."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                COUNT(review_id) as total_reviews,
                ROUND(AVG(rating), 2) as average_rating,
                ROUND(AVG(sentiment_score), 2) as average_sentiment,
                SUM(CASE WHEN sentiment_score > 0 THEN 1 ELSE 0 END) as positive_reviews,
                SUM(CASE WHEN sentiment_score < 0 THEN 1 ELSE 0 END) as negative_reviews,
                SUM(CASE WHEN sentiment_score = 0 THEN 1 ELSE 0 END) as neutral_reviews
            FROM review
            WHERE branch_id = %s
        """, (branch_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving sentiment summary: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_rating_breakdown(branch_id):
    """Retrieves the count of each rating value for a branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT rating, COUNT(review_id) as count
            FROM review
            WHERE branch_id = %s
            GROUP BY rating
            ORDER BY rating DESC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving rating breakdown: {e}")
        return []

    finally:
        close_connection(conn, cursor)