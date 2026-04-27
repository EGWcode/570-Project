"""
HQ / Admin Dashboard – Implementation Notes

Purpose:
Centralized dashboard for monitoring all restaurant branches in real time.
Displays operational data, analytics, and live system activity.

--------------------------------------------------
DATA SOURCES
--------------------------------------------------

MySQL:
- orders, order_item, payment
- reservations, party
- inventory_item, supplier
- branch, employee, shift_schedule

MongoDB:
- reviews
- sentiment data
- clickstream/menu interaction data

Redis:
- real-time event feed (simulation script + UI actions)
- events:
    new_order
    reservation_created
    reservation_seated
    order_completed
    inventory_low
    new_review

--------------------------------------------------
CORE SECTIONS TO BUILD
--------------------------------------------------

1. KPI SUMMARY (Top Row)
- Total Sales (sum payment.amount)
- Active Orders (orders where status = IN_PROGRESS)
- Reservations Today
- Average Rating
- Low Inventory Count

--------------------------------------------------

2. BRANCH PERFORMANCE CARDS
Display per branch:
- branch_name
- total_sales
- active_orders
- reservations_today
- avg_rating
- low_stock_count

--------------------------------------------------

3. LIVE ACTIVITY FEED (IMPORTANT FEATURE)
- Pull from Redis OR simulate with periodic refresh
- Show latest system events

Display format:
[Branch Name] Event Message

Examples:
[Hampton] New Order Created (Order ID: 12)
[Norfolk] Reservation Created (Party Size: 4)
[Virginia Beach] Inventory Low: Shrimp

Color coding:
- Hampton → blue
- Norfolk → green
- Virginia Beach → orange

--------------------------------------------------

4. ORDERS PANEL
- order_id
- branch
- status (IN_PROGRESS, SERVED, COMPLETED)
- total_amount

--------------------------------------------------

5. RESERVATIONS PANEL
- reservation_datetime
- branch
- party_size
- status (CONFIRMED, SEATED)

--------------------------------------------------

6. INVENTORY ALERTS
- item_name
- branch
- quantity_on_hand
- reorder_level

Condition:
quantity_on_hand < reorder_level

--------------------------------------------------

7. REVIEWS / FEEDBACK
- rating
- comments
- branch
- sentiment_score (if available)

--------------------------------------------------

8. STAFFING (Optional if time)
- employees scheduled today
- branch staffing coverage

--------------------------------------------------

REAL-TIME BEHAVIOR
--------------------------------------------------

- Page should refresh every few seconds OR listen to Redis
- Must reflect:
    - simulation script activity
    - customer website activity
    - employee/manager actions

--------------------------------------------------

GOAL
--------------------------------------------------

Show that FLOW supports enterprise restaurant operations:
- multi-branch monitoring
- real-time updates
- analytics + operational data combined
"""