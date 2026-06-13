from fastapi import FastAPI
from pydantic import BaseModel
from database import (
    SessionLocal,
    User,
    Item,
    ScanResult,
    UserPoint,
    Voucher,
    RedeemHistory,
    RewardHistory
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


def generate_voucher_code():

    return ''.join(

        random.choices(

            string.ascii_uppercase +

            string.digits,

            k=6
        )
    )

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

        # ================= AUTO STATUS =================

        if item.created_at:

            item.status = calculate_status(
                item.created_at,
                item.expiry_days
            )

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
                f"{item.expiry_days} Days Left",

            "badge":
                f"{item.expiry_days} DAYS LEFT",

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

        title="Voucher A",

        description="Discount 10%",

        points_required=100,

        image="voucher_a_images.png",

        status="available"
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

            "points":
            voucher.points_required,

            "image":
            voucher.image,

            "status":
            voucher.status
        })

    return result


@app.post("/redeem-voucher")
def redeem_voucher(
    data: RedeemVoucherModel
):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:

        return {
            "status":"error"
        }

    voucher = db.query(
        Voucher
    ).filter(
        Voucher.voucher_id ==
        data.voucher_id
    ).first()

    if not voucher:

        return {
            "status":"error"
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

        result.append({

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

    return {
        "status": "success"
    }