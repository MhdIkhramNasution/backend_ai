from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from database import (
    SessionLocal,
    User,
    Item,
    ScanResult,
    UserPoint,
    Voucher,
    RedeemHistory,
    RewardHistory,
    ActivityHistory
)
from datetime import datetime
import bcrypt
from database import UserPoint
from database import RewardHistory
import os
import random
import string

app = FastAPI()

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ================= REGISTER MODEL =================

class RegisterModel(BaseModel):
    username: str
    email: str
    phone: str
    password: str

# ================= LOGIN MODEL =================

class LoginModel(BaseModel):
    username: str
    password: str


class SaveScanModel(BaseModel):

    username: str

    image: str

    prediction: str

    confidence: str


class RedeemVoucherModel(BaseModel):

    username: str

    voucher_id: int

def save_activity(
    db,
    user_id,
    activity
):

    history = ActivityHistory(

        user_id=user_id,

        activity=activity
    )

    db.add(history)

    db.commit()

    # ================= KEEP ONLY 20 LATEST =================

    histories = db.query(
        ActivityHistory
    ).filter(

        ActivityHistory.user_id == user_id

    ).order_by(

        ActivityHistory.id.desc()

    ).all()

    if len(histories) > 10:

        for h in histories[10:]:

            db.delete(h)

        db.commit()

def generate_voucher_code():

    return ''.join(

        random.choices(

            string.ascii_uppercase +

            string.digits,

            k=6
        )
    )

# ================= WEBSOCKET =================

active_connections = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(
    websocket: WebSocket,
    username: str
):

    await websocket.accept()

    active_connections[
        username
    ] = websocket

    print(
        f"{username} connected"
    )

    try:

        while True:

            await websocket.receive_text()

    except:

        active_connections.pop(
            username,
            None
        )

        print(
            f"{username} disconnected"
        )

async def send_notification(
    username,
    title,
    message,
    type_
):

    websocket = active_connections.get(
        username
    )

    if websocket:

        await websocket.send_json({

            "title":
            title,

            "message":
            message,

            "type":
            type_
        })


@app.get("/test-notification/{username}")
async def test_notification(
    username: str
):

    await send_notification(

        username,

        "Item Expiring Soon",

        "Banana expires tomorrow",

        "warning"
    )

    return {
        "status":"sent"
    }

# ================= REGISTER API =================

@app.post("/register")
def register(data: RegisterModel):

    db = SessionLocal()

    # CEK EMAIL
    existing_email = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_email:

        return {
            "status": "error",
            "message": "Email already exists"
        }

    # CEK USERNAME
    existing_username = db.query(User).filter(
        User.username == data.username
    ).first()

    if existing_username:

        return {
            "status": "error",
            "message": "Username already exists"
        }

    # HASH PASSWORD
    hashed_password = bcrypt.hashpw(
        data.password.encode('utf-8'),
        bcrypt.gensalt()
    )

    # BUAT USER BARU
    new_user = User(
        username=data.username,
        email=data.email,
        phone=data.phone,
        password=hashed_password.decode('utf-8')
    )

    db.add(new_user)
    db.commit()

    db.refresh(new_user)

    new_point = UserPoint(
        user_id=new_user.id,
        points=0
    )

    db.add(new_point)
    db.commit()

    return {
        "status": "success",
        "message": "Register successful"
    }

# ================= LOGIN API =================

@app.post("/login")
def login(data: LoginModel):

    db = SessionLocal()

    # CEK USERNAME
    user = db.query(User).filter(
        User.username == data.username
    ).first()

    # USERNAME TIDAK ADA
    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    # CEK PASSWORD
    valid_password = bcrypt.checkpw(
        data.password.encode('utf-8'),
        user.password.encode('utf-8')
    )

    # PASSWORD SALAH
    if not valid_password:

        return {
            "status": "error",
            "message": "Wrong password"
        }

    # LOGIN BERHASIL
    return {
        "status": "success",
        "message": "Login successful",
        "username": user.username,
        "email": user.email,
        "phone": user.phone
    }
# ================= UPDATE ACCOUNT MODEL =================

class UpdateAccountModel(BaseModel):

    username: str

    new_username: str

    email: str

    phone: str

    new_password: str = ""  

# ================= INVENTORY MODEL =================

class InventoryModel(BaseModel):

    username: str
    item_name: str
    image: str
    expiry_days: int
    status: str

# ================= MANUAL ADD ITEM MODEL =================

class ManualItemModel(BaseModel):

    username: str

    item_name: str

    category: str

    expiry_date: str

    notes: str
# ================= UPDATE ACCOUNT API =================

@app.post("/update-account")
def update_account(data: UpdateAccountModel):

    print("USERNAME LAMA = ${UserSession.username}");
    print("USERNAME BARU = $username");

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    user.username = data.new_username
    user.email = data.email
    user.phone = data.phone

    if data.new_password.strip() != "":

        hashed_password = bcrypt.hashpw(
            data.new_password.encode('utf-8'),
            bcrypt.gensalt()
        )

        user.password = hashed_password.decode('utf-8')

    db.commit()

    return {
        "status": "success",
        "message": "Account updated"
    }

def calculate_status(
    created_at,
    expiry_days
):

    created_date = datetime.fromisoformat(
        created_at
    )

    days_passed = (
        datetime.now() -
        created_date
    ).days

    remaining_days = (
        expiry_days -
        days_passed
    )

    if remaining_days <= 0:
        return "Expired"

    elif remaining_days <= 5:
        return "Almost Expired"

    return "Fresh"

@app.post("/inventory/add")
def add_inventory(data: InventoryModel):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    existing_item = db.query(Item).filter(
        Item.user_id == user.id,
        Item.item_name == data.item_name
    ).first()

    if existing_item:

        existing_item.stock += 1

        db.commit()

        return {
            "status": "success",
            "message": "Stock updated"
        }

    new_item = Item(
        user_id=user.id,
        item_name=data.item_name,
        stock=1,
        image=data.image,
        expiry_days=data.expiry_days,
        status="Fresh",
        created_at=str(datetime.now())
    )

    db.add(new_item)

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    if point:
        point.points += 10

    db.commit()

    save_activity(

        db,

        user.id,

        f"Added {data.item_name} to inventory"
    )

    return {
        "status": "success",
        "message": "Item added"
    }

# ================= GET INVENTORY =================

@app.get("/inventory/{username}")
def get_inventory(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return []

    items = db.query(Item).filter(
        Item.user_id == user.id
    ).order_by(
        Item.item_id.desc()
    ).all()

    result = []

    for item in items:

        remaining_days = item.expiry_days

        # ================= AUTO STATUS =================

        if item.created_at:

            item.status = calculate_status(
                item.created_at,
                item.expiry_days
            )

            created_date = datetime.fromisoformat(
                item.created_at
            )

            days_passed = (
                datetime.now() -
                created_date
            ).days

            remaining_days = max(
                0,
                item.expiry_days -
                days_passed
            )

        # ================= AUTO WEBSOCKET =================

        if (
            remaining_days <= 2 and
            remaining_days > 0 and
            not item.expiring_notified
        ):

            try:

                import asyncio

                asyncio.create_task(

                    send_notification(

                        username,

                        "Item Expiring Soon",

                        f"{item.item_name} will expire in {remaining_days} day(s)",

                        "warning"
                    )
                )

                item.expiring_notified = True

            except Exception as e:

                print(e)

        if (
            remaining_days <= 0 and
            not item.expired_notified
        ):

            try:

                import asyncio

                asyncio.create_task(

                    send_notification(

                        username,

                        "Item Expired",

                        f"{item.item_name} has expired",

                        "danger"
                    )
                )

                item.expired_notified = True

            except Exception as e:

                print(e)

        # ================= COLOR =================

        if item.status == "Fresh":

            color = 0xFF4CAF50
            progress = 1.0

        elif item.status == "Almost Expired":

            color = 0xFFFF9800
            progress = 0.5

        else:

            color = 0xFFF44336
            progress = 0.2

        result.append({

            "id": item.item_id,

            "title": item.item_name,

            "stock": item.stock,

            "image": item.image,

            "subtitle":
                f"{remaining_days} DAYS LEFT",

            "badge":
                f"{remaining_days} DAYS LEFT",

            "status": item.status,

            "color": color,

            "progress": progress
        })

    db.commit()

    return result

# ================= GET INVENTORY =================

@app.get("/scan/history/{username}")
def get_scan_history(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        return []

    scans = db.query(
        ScanResult
    ).filter(
        ScanResult.user_id == user.id
    ).order_by(
        ScanResult.scan_id.desc()
    ).all()

    result = []

    for scan in scans:

        result.append({

            "id":
                scan.scan_id,

            "image":
                scan.image,

            "prediction":
                scan.prediction,

            "confidence":
                scan.confidence,

            "date":
                scan.scanned_at
        })

    return result

# ================= REDUCE STOCK =================

@app.put("/inventory/reduce/{item_id}")
def reduce_stock(item_id: int):

    db = SessionLocal()

    item = db.query(Item).filter(
        Item.item_id == item_id
    ).first()

    if not item:

        return {
            "status": "error"
        }

    item.stock -= 1

    if item.stock <= 0:

        db.delete(item)

    db.commit()

    return {
        "status": "success"
    }

@app.get("/points/{username}")
def get_points(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return {"points": 0}

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    if not point:
        return {"points": 0}

    return {
        "points": point.points
    }

@app.get("/reward-history/{username}")
def reward_history(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return []

    rewards = db.query(
        RewardHistory
    ).filter(
        RewardHistory.user_id == user.id
    ).all()

    result = []

    for reward in rewards:

        result.append({

            "reward_name":
            reward.reward_name,

            "points_used":
            reward.points_used,

            "redeemed_at":
            reward.redeemed_at,
        })

    return result
@app.get("/leaderboard")
def leaderboard():

    db = SessionLocal()

    users = db.query(
        User,
        UserPoint
    ).join(

        UserPoint,
        User.id == UserPoint.user_id

    ).order_by(
        UserPoint.points.desc()
    ).all()

    result = []

    for user, point in users:

        result.append({

            "username":
            user.username,

            "points":
            point.points,
        })

    return result

@app.get("/inventory/expired/{username}")
def expired_inventory(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return []

    items = db.query(Item).filter(
        Item.user_id == user.id,
        Item.expiry_days <= 3
    ).all()

    result = []

    for item in items:

        result.append({

            "name":
            item.item_name,

            "days_left":
            item.expiry_days,
        })

    return result

@app.get("/dashboard/{username}")
def dashboard(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return {}

    total_items = db.query(Item).filter(
        Item.user_id == user.id
    ).count()

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    return {

        "total_items":
        total_items,

        "eco_points":
        point.points if point else 0
    }

class RedeemModel(BaseModel):

    username: str
    reward_name: str
    points_required: int


@app.post("/redeem")
def redeem_reward(data: RedeemModel):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    if not point:

        return {
            "status": "error",
            "message": "Point record not found"
        }

    if point.points < data.points_required:

        return {
            "status": "error",
            "message": "Not enough points"
        }

    point.points -= data.points_required

    reward = RewardHistory(
        user_id=user.id,
        reward_name=data.reward_name,
        points_used=data.points_required,
        redeemed_at=str(datetime.now())
    )

    db.add(reward)

    db.commit()

    return {
        "status": "success",
        "message": "Reward redeemed"
    }

@app.get("/fix-points/{username}")
def fix_points(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return {"message": "user not found"}

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    if point:
        return {"message": "already exists"}

    new_point = UserPoint(
        user_id=user.id,
        points=500
    )

    db.add(new_point)
    db.commit()

@app.get("/profile/{username}")
def get_profile(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    return {

        "username": user.username,

        "email": user.email,

        "phone": user.phone,

        "points":
        point.points if point else 0
    }

@app.get("/goals/{username}")
def get_goals(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return {
            "status": "error",
            "message": "User not found"
        }

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    points = point.points if point else 0

    if points < 200:
        badge = "Eco Starter"
        next_badge = "Eco Hero"
        target = 200

    elif points < 500:
        badge = "Eco Hero"
        next_badge = "Eco Champion"
        target = 500

    else:
        badge = "Eco Champion"
        next_badge = "MAX"
        target = 900

    progress = min(points / target, 1.0)

    return {
        "points": points,
        "badge": badge,
        "next_badge": next_badge,
        "progress": progress
    }

    return {"message": "point created"}

@app.post("/create-voucher")
def create_voucher():

    db = SessionLocal()

    voucher = Voucher(

        title="Eco Market Voucher",

        description=
        "Get 20% discount for eco-friendly products",

        image=
        "assets/vouchers/eco_market.png",

        category=
        "Shopping",

        discount_percent=20,

        max_discount=50000,

        min_transaction=100000,

        points_required=100,

        quota=50,

        expired_at=
        "2026-12-31",

        terms=
        "Valid for eco-friendly products only",

        status="active"
    )

    db.add(voucher)

    db.commit()

    return {
        "status":"success"
    }


@app.get("/vouchers")
def get_vouchers():

    db = SessionLocal()

    vouchers = db.query(
        Voucher
    ).all()

    result = []

    for voucher in vouchers:

        result.append({

            "voucher_id":
            voucher.voucher_id,

            "title":
            voucher.title,

            "description":
            voucher.description,

            "image":
            voucher.image,

            "category":
            voucher.category,

            "discount_percent":
            voucher.discount_percent,

            "max_discount":
            voucher.max_discount,

            "min_transaction":
            voucher.min_transaction,

            "points":
            voucher.points_required,

            "quota":
            voucher.quota,

            "expired_at":
            voucher.expired_at,

            "terms":
            voucher.terms,

            "status":
            voucher.status
        })

    return result


@app.post("/redeem-voucher")
def redeem_voucher(data: RedeemVoucherModel):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:
        return {"status": "error", "message": "User not found"}

    voucher = db.query(Voucher).filter(
        Voucher.voucher_id == data.voucher_id 
    ).first()

    if not voucher:
        return {"status": "error", "message": "Voucher not found"}

    point = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    if not point or point.points < voucher.points_required:  
        return {"status": "error", "message": "Insufficient points"}

    old_history = db.query(RedeemHistory).filter(
        RedeemHistory.user_id == user.id,
        RedeemHistory.voucher_id == data.voucher_id
    ).all()

    for old in old_history:
        db.delete(old)

    db.commit()

    # Kurangi poin
    point.points -= voucher.points_required 

    # Generate & simpan kode baru
    voucher_code = generate_voucher_code()

    new_history = RedeemHistory(
        user_id=user.id,
        voucher_id=data.voucher_id,
        voucher_code=voucher_code,
        redeemed_at=str(datetime.now())
    )

    db.add(new_history)
    db.commit()

    return {
        "status": "success",
        "voucher_code": voucher_code
    }
# ================= SOLD OUT CHECK =================

    if voucher.quota is None:

        voucher.quota = 50

    if voucher.quota <= 0:

        return {

            "status": "error",

            "message": "Voucher sold out"
        }

    point = db.query(
        UserPoint
    ).filter(
        UserPoint.user_id ==
        user.id
    ).first()

    if point.points < voucher.points_required:

        return {
            "status":"error",
            "message":"Not enough points"
        }

    point.points -= voucher.points_required
    voucher.quota -= 1
    voucher_code = generate_voucher_code()

    redeem = RedeemHistory(

        user_id=user.id,

        voucher_id=voucher.voucher_id,

        redeemed_at=str(
            datetime.now()
        ),

        voucher_code=
        voucher_code,

        status="available"
    )

    db.add(redeem)

    db.commit()

    save_activity(

        db,

        user.id,

        f"Redeemed {voucher.title}"
    )

    return {
    "status": "success",
    "voucher_code": voucher_code
}

@app.get("/user-points/{username}")
def get_user_points(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    point = db.query(
        UserPoint
    ).filter(
        UserPoint.user_id == user.id
    ).first()

    if not point:

        return {
            "points": 0
        }

    return {
        "points": point.points
    }

@app.get("/redeem-history/{username}")
def redeem_history(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        return []

    histories = db.query(
        RedeemHistory
    ).filter(
        RedeemHistory.user_id == user.id
    ).all()

    result = []

    for history in histories:

        voucher = db.query(
            Voucher
        ).filter(
            Voucher.voucher_id ==
            history.voucher_id
        ).first()

        if not voucher:
            continue

        result.append({

            "voucher_id":
            voucher.voucher_id,

            "voucher_name":
            voucher.title,

            "points_used":
            voucher.points_required,

            "voucher_code":
            history.voucher_code,

            "redeemed_at":
            history.redeemed_at,

            "status":
            history.status
        })

    return result
@app.post("/create-badges")
def create_badges():

    db = SessionLocal()

    badges = [

        Badge(
            name="Eco Starter",
            required_points=100,
            image="eco_starter.png"
        ),

        Badge(
            name="Eco Hero",
            required_points=500,
            image="eco_hero.png"
        ),

        Badge(
            name="Eco Champion",
            required_points=900,
            image="eco_champion.png"
        ),
    ]

    db.add_all(badges)

    db.commit()

    return {
        "status":"success"
    }

@app.get("/badges/{username}")
def get_badges(username:str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return []

    point = db.query(
        UserPoint
    ).filter(
        UserPoint.user_id == user.id
    ).first()

    user_points = 0

    if point:
        user_points = point.points

    badges = db.query(
        Badge
    ).all()

    result = []

    for badge in badges:

        result.append({

            "name":
            badge.name,

            "image":
            badge.image,

            "required_points":
            badge.required_points,

            "unlocked":
            user_points >=
            badge.required_points
        })

    return result

@app.post("/scan/save")
def save_scan(
    data: SaveScanModel
):
    print("SCAN SAVE CALLED")
    print(data)

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    scan = ScanResult(

        user_id=user.id,

        image=data.image,

        prediction=data.prediction,

        confidence=data.confidence,

        scanned_at=str(
            datetime.now()
        )
    )

    db.add(scan)

    db.commit()

    save_activity(

        db,

        user.id,

        f"Scanned {data.prediction}"
    )

    return {
        "status": "success"
    }

@app.post("/inventory/manual-add")
def manual_add(
    data: ManualItemModel
):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:
        return {
            "status": "error",
            "message": "User not found"
        }

    # ================= AUTO IMAGE =================

    image_name = (
        data.item_name
        .strip()
        .lower()
        .replace(" ", "_")
    )

    image_path = (
        f"assets/images/{image_name}.png"
    )

    # ================= EXPIRY DAYS =================

    expiry_days = 7

    item = Item(

        user_id=user.id,

        item_name=data.item_name,

        stock=1,

        image=image_path,

        expiry_days=expiry_days,

        status="Fresh",

        created_at=str(
            datetime.now()
        )
    )

    db.add(item)

    db.commit()

    save_activity(

        db,

        user.id,

        f"Added {data.item_name} manually"
    )

    return {

        "status": "success",

        "item": {

            "name": data.item_name,

            "image": image_path,

            "expiry_days": expiry_days
        }
    }

@app.put("/inventory/reduce-stock/{item_id}")
def reduce_stock(item_id: int):

    db = SessionLocal()

    item = db.query(Item).filter(
        Item.item_id == item_id
    ).first()

    if not item:

        return {
            "status": "error"
        }

    if item.stock > 0:

        item.stock -= 1

    if item.stock <= 0:

        db.delete(item)

    db.commit()

    save_activity(

        db,

        item.user_id,

        f"Reduced stock of {item.item_name}"
    )

    return {
        "status": "success"
    }

# ============= HISTORY STATS ==========
@app.get("/history/{username}")
def get_history(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return []

    histories = db.query(
        ActivityHistory
    ).filter(

        ActivityHistory.user_id == user.id

    ).order_by(

        ActivityHistory.id.desc()

    ).limit(20).all()

    result = []

    for h in histories:

        result.append({

            "activity":
            h.activity,

            "time":
            h.created_at.strftime(
                "%d %b %Y %H:%M"
            )
        })

    return result

# ================= DASHBOARD STATS =================

@app.get("/dashboard-stats/{username}")
def dashboard_stats(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        return {
            "status": "error"
        }

    items = db.query(Item).filter(
        Item.user_id == user.id
    ).all()

    fresh = 0
    almost_expired = 0
    expired = 0

    for item in items:

        if item.created_at:

            item.status = calculate_status(
                item.created_at,
                item.expiry_days
            )

        if item.status == "Fresh":

            fresh += 1

        elif item.status == "Almost Expired":

            almost_expired += 1

        else:

            expired += 1

    points = db.query(UserPoint).filter(
        UserPoint.user_id == user.id
    ).first()

    total_points = 0

    if points:

        total_points = points.points

    badge_count = 0

    if total_points >= 50:
        badge_count = 1

    if total_points >= 150:
        badge_count = 2

    if total_points >= 300:
        badge_count = 3

    return {

        "total_items": len(items),

        "fresh": fresh,

        "almost_expired": almost_expired,

        "expired": expired,

        "points": total_points,

        "badges": badge_count
    }

# ================= NOTIFICATIONS =================

@app.get("/notifications/{username}")
def get_notifications(username: str):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return []

    items = db.query(Item).filter(
        Item.user_id == user.id
    ).all()

    notifications = []

    for item in items:

        # Pastikan status selalu update
        if item.created_at:

            item.status = calculate_status(
                item.created_at,
                item.expiry_days
            )

        # ================= EXPIRED =================

        if item.status == "Expired":

            notifications.append({

                "title":
                "Item Expired!",

                "message":
                f"Your {item.item_name} has expired.",

                "type":
                "danger"
            })

        # ================= ALMOST EXPIRED =================

        elif item.status == "Almost Expired":

            notifications.append({

                "title":
                "Item Expiring Soon!",

                "message":
                f"Your {item.item_name} will expire soon.",

                "type":
                "warning"
            })

    db.commit()

    return notifications

@app.get("/voucher-code/{username}/{voucher_id}")
def get_voucher_code(username: str, voucher_id: int):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return {"voucher_code": ""}

    history = db.query(RedeemHistory).filter(
        RedeemHistory.user_id == user.id,
        RedeemHistory.voucher_id == voucher_id
    ).first() 
    if not history:
        return {"voucher_code": ""}

    return {"voucher_code": history.voucher_code}