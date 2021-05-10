from cowin import CowinApp, Telegram, Session
import time


def criterion(session):
    if session['vaccine'] == "COVAXIN" and session['min_age_limit'] == 18:
        return True
    return False


if __name__ == '__main__':
    locationOfInterest = {
        "Haryana": ["Gurgaon"],
        "Delhi": ["West Delhi", "South West Delhi", "Central Delhi", "New Delhi", "South East Delhi", "South Delhi"],
    }

    cowin = CowinApp()
    tg = Telegram()
    districtsIds = cowin.getDistrictsOfInterest(locationOfInterest)

    while True:
        time.sleep(5)
        sessions = cowin.getAvailableSessions(districtsIds, criterion)
        if len(sessions) > 0:
            cowin.book(sessions)
            for session in sessions:
                tg.sendMessage(str(session))