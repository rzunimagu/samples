from typing import Optional, TypedDict, Tuple, Dict, List, NewType


SocialAccountEmail = TypedDict("SocialAccountEmail", {'email': str, 'verified': bool})
SocialAccountList = TypedDict("SocialAccountList", {
    'vk': Optional[str],
    'discord': Optional[str],
    'battlenet': Optional[str],
    'email': Optional[SocialAccountEmail],
    'login': str,
    'password': bool,
    'number': int,
})
SelectOptionInt = Tuple[int, str]
SelectOptionBool = Tuple[bool, str]
SelectOptionStr = Tuple[str, str]
UuidStr = str
TimeStr = str

TimetableOption = TypedDict("TimetableOption", {
    "start": TimeStr,
    "end": Optional[TimeStr],
    "rounds": int,
})
TimetableDayList = List[TimetableOption]
TimetableDict = NewType("TimetableDict", Dict)

TimetableDayDict = TypedDict("TimetableDayDict", {
    "name": str,
    "hours": TimetableOption
})
TimeTableList = List[TimetableDayDict]
