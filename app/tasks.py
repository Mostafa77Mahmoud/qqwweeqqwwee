import logging
from datetime import datetime, timedelta
from app import db
from app.models import BackupLog, Transaction, Order
from app.utils import create_backup, cleanup_old_backups

logger = logging.getLogger(__name__)

def daily_backup_task():
    """Daily backup task - can be called by cron or scheduler"""
    try:
        logger.info("Starting daily backup task")
        filename = create_backup()
        logger.info(f"Daily backup completed: {filename}")
        return True
    except Exception as e:
        logger.error(f"Daily backup failed: {e}")
        return False

def weekly_cleanup_task():
    """Weekly cleanup task for old files and logs"""
    try:
        logger.info("Starting weekly cleanup task")
        
        # Clean old backups
        cleanup_old_backups(retention_days=30)
        
        # Clean old transaction logs (optional - keep last 1 year)
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        old_transactions_count = Transaction.query.filter(
            Transaction.created_at < cutoff_date,
            Transaction.reference_type == 'manual'  # Only clean manual transactions
        ).count()
        
        if old_transactions_count > 0:
            logger.info(f"Found {old_transactions_count} old transactions to archive")
            # TODO: Archive old transactions instead of deleting
        
        logger.info("Weekly cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"Weekly cleanup failed: {e}")
        return False

def generate_daily_report():
    """Generate daily summary report"""
    try:
        today = datetime.utcnow().date()
        
        # Calculate daily stats
        from sqlalchemy import func, and_
        
        day_income = db.session.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.type == 'income',
                func.date(Transaction.created_at) == today
            )
        ).scalar() or 0
        
        day_expense = db.session.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.type == 'expense',
                func.date(Transaction.created_at) == today
            )
        ).scalar() or 0
        
        orders_count = Order.query.filter(
            func.date(Order.created_at) == today
        ).count()
        
        completed_orders = Order.query.filter(
            and_(
                func.date(Order.created_at) == today,
                Order.status == 'completed'
            )
        ).count()
        
        report = {
            'date': today.isoformat(),
            'income': float(day_income),
            'expense': float(day_expense),
            'net_income': float(day_income - day_expense),
            'total_orders': orders_count,
            'completed_orders': completed_orders,
            'completion_rate': (completed_orders / orders_count * 100) if orders_count > 0 else 0
        }
        
        logger.info(f"Daily report generated: {report}")
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return None

def health_check():
    """System health check"""
    try:
        issues = []
        
        # Check database connectivity
        try:
            db.session.execute(db.text('SELECT 1')).fetchone()
        except Exception as e:
            issues.append(f"Database connectivity issue: {e}")
        
        # Check recent backups
        recent_backup = BackupLog.query.filter_by(status='success').order_by(
            BackupLog.created_at.desc()
        ).first()
        
        if not recent_backup:
            issues.append("No successful backups found")
        elif recent_backup.created_at < datetime.utcnow() - timedelta(days=7):
            issues.append("No recent backups (older than 7 days)")
        
        # Check disk space (basic check)
        import shutil
        try:
            total, used, free = shutil.disk_usage('.')
            free_gb = free / (1024**3)
            if free_gb < 1:  # Less than 1GB free
                issues.append(f"Low disk space: {free_gb:.1f}GB free")
        except:
            pass  # Can't check disk space
        
        status = {
            'healthy': len(issues) == 0,
            'issues': issues,
            'checked_at': datetime.utcnow().isoformat()
        }
        
        if issues:
            logger.warning(f"Health check found issues: {issues}")
        else:
            logger.info("Health check passed")
        
        return status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'healthy': False,
            'issues': [f"Health check error: {e}"],
            'checked_at': datetime.utcnow().isoformat()
        }

# Scheduler setup (if using APScheduler)
def setup_scheduler():
    """Setup background task scheduler"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        # Daily backup at 2 AM
        scheduler.add_job(
            daily_backup_task,
            CronTrigger(hour=2, minute=0),
            id='daily_backup',
            name='Daily Database Backup',
            replace_existing=True
        )
        
        # Weekly cleanup on Sundays at 3 AM
        scheduler.add_job(
            weekly_cleanup_task,
            CronTrigger(day_of_week=6, hour=3, minute=0),
            id='weekly_cleanup',
            name='Weekly Cleanup Task',
            replace_existing=True
        )
        
        # Daily report generation at 11:59 PM
        scheduler.add_job(
            generate_daily_report,
            CronTrigger(hour=23, minute=59),
            id='daily_report',
            name='Daily Report Generation',
            replace_existing=True
        )
        
        # Health check every hour
        scheduler.add_job(
            health_check,
            CronTrigger(minute=0),
            id='health_check',
            name='Hourly Health Check',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background scheduler started")
        return scheduler
        
    except ImportError:
        logger.warning("APScheduler not available. Background tasks disabled.")
        return None
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")
        return None
