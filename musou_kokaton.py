import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.boost_speed = 20  # スピードアップ時の速度
        self.state = "normal"  # 状態管理（通常: "normal", 無敵: "hyper"）
        self.hyper_life = 0  # 無敵状態の残りフレーム数

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]

        # スピードアップの処理
        current_speed = self.boost_speed if key_lst[pg.K_LSHIFT] else self.speed

        self.rect.move_ip(current_speed * sum_mv[0], current_speed * sum_mv[1])

        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-current_speed * sum_mv[0], -current_speed * sum_mv[1])

        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        # 無敵状態の処理
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)  # 無敵時の画像変換
            self.hyper_life -= 1
            if self.hyper_life <= 0:
                self.state = "normal"

        screen.blit(self.image, self.rect)
        
class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス
    """
    def __init__(self, bird: Bird, life: int):
        """
        防御壁を生成する
        引数1 bird：こうかとん
        引数2 life：防御壁の発動時間
        """
        super().__init__()
        self.bird = bird
        self.life = life

        # 防御壁の初期設定
        self.image = pg.Surface((20, bird.rect.height * 2), pg.SRCALPHA)
        pg.draw.rect(self.image, (0, 0, 255, 128), (0, 0, 20, bird.rect.height * 2))
        self.rect = self.image.get_rect()
        vx, vy = bird.dire
        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()
        self.rect.center = bird.rect.centerx + vx * bird.rect.width, bird.rect.centery + vy * bird.rect.height

    def update(self):
        """
        防御壁の位置と残り時間を更新する
        """
        self.life -= 1
        if self.life <= 0:
            self.kill()
    


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        if self.state == "active":
            self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        elif self.state == "inactive":
            self.rect.move_ip((self.speed/2)*self.vx, (self.speed/2)*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: float = 0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        引数 angle0：ビームの回転角度
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    複数方向にビームを発射するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        NeoBeamクラスのイニシャライザ
        引数 bird：ビームを放つこうかとん
        引数 num：発射するビームの数
        """
        self.beams = self.gen_beams(bird, num)

    def gen_beams(self, bird: Bird, num: int) -> list[Beam]:
        """
        指定された数のビームを生成する
        引数 bird：ビームを放つこうかとん
        引数 num：発射するビームの数
        戻り値：生成されたビームのリスト
        """
        angles = range(-50, 51, 100 // (num - 1))
        return [Beam(bird, angle) for angle in angles]


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表示する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP:
    """
    EMP（電磁パルス）攻撃に関するクラス
    """
    def __init__(self, enemies: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        """
        EMP攻撃を初期化する
        引数1 enemies：敵機のグループ
        引数2 bombs：爆弾のグループ
        引数3 screen：画面Surface
        """
        self.enemies = enemies
        self.bombs = bombs
        self.screen = screen

    def activate(self):
        """
        EMP攻撃を発動し、敵機と爆弾を無効化する
        """
        for enemy in self.enemies:
            enemy.interval = float('inf')
            enemy.image = pg.transform.laplacian(enemy.image)
        for bomb in self.bombs:
            bomb.speed /= 2
            bomb.state = "inactive"
        self.display_effect()

    def display_effect(self):
        """
        EMP発動時の視覚効果を表示する
        """
        overlay = pg.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(128)  # 透明度を設定
        overlay.fill((255, 255, 0))  # 黄色に設定
        self.screen.blit(overlay, (0, 0))
        pg.display.update()
        pg.time.delay(50)  # 0.05秒表示


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life:int):
        """
        重力場の初期化
        引数:
            life (int):重力場の持続時間（フレーム数）
        """
        super().__init__()
        self.image = pg.Surface((WIDTH,HEIGHT)) #画面全体を覆うSurface
        self.image.fill((0,0,0)) #黒色で塗りつぶす
        self.image.set_alpha(128) #半透明にする（透明度128）
        self.rect = self.image.get_rect() #Surfaceの矩形領域
        self.life = life #重力場の時間を設定


    def update(self):
        """
        重力場の更新
        lifeを減算し、0未満になったら自動的に削除
        """
        self.life -= 1 #1フレームごとに減算
        if self.life < 0:
            self.kill() #重力場を削除


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    shields = pg.sprite.Group()
    gravities = pg.sprite.Group()  # 重力場グループの初期化

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                # スペースキーが押された場合のみビームを発射
                if event.key == pg.K_SPACE:
                    if key_lst[pg.K_z]:  # Zキーとスペースキーで弾幕発動
                        neo_beam = NeoBeam(bird, 5)  # ビームを5方向に発射
                        beams.add(*neo_beam.beams)
                    else:  # 通常ビーム発射
                        beams.add(Beam(bird))
                # EMPの発動条件（Eキー押下）
                if event.key == pg.K_e and score.value >= 20:
                    emp = EMP(emys, bombs, screen)
                    emp.activate()
                    score.value -= 20
                # 無敵状態の発動条件（右Shiftキー）
                if event.key == pg.K_RSHIFT and score.value >= 100 and bird.state == "normal":
                    bird.state = "hyper"
                    bird.hyper_life = 500  # 無敵時間
                    score.value -= 100  # スコア消費
                # 防御壁の発動条件（Sキー押下）
                if event.key == pg.K_s and score.value >= 50 and len(shields) == 0:
                    shields.add(Shield(bird, 400))
                    score.value -= 50
                elif event.key == pg.K_g and score.value >= 200:
                    score.value -= 200  # スコアを200消費
                    gravities.add(Gravity(400))  # 重力場を発生

        # 背景描画
        screen.blit(bg_img, [0, 0])

        # 敵機の生成
        if tmr % 200 == 0:
            emys.add(Enemy())

        # 敵機が停止したら爆弾を投下
        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        # 衝突処理
        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.image = pg.transform.rotozoom(pg.image.load(f"fig/6.png"), 0, 0.9)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))
                score.value += 1
            else:
                bird.change_img(8, screen)
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        # 防御壁と爆弾の衝突処理
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))

        # 重力場と爆弾・敵機の衝突判定
        for gravity in gravities: #重力場を順に処理
            for bomb in pg.sprite.spritecollide(gravity, bombs, True): #重力場と爆弾の衝突判定（衝突した爆弾は削除）
                exps.add(Explosion(bomb, 50)) #爆発エフェクトを追加
                score.value += 1 #スコアを1点追加
            for emy in pg.sprite.spritecollide(gravity, emys, True): #重力場と敵機の衝突判定（衝突した敵機は削除）
                exps.add(Explosion(emy, 100)) #爆発エフェクトを追加
                score.value += 10 #スコアを10点追加

        # 各オブジェクトの更新と描画
        shields.update()
        shields.draw(screen)

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        gravities.update()  # 重力場の更新
        gravities.draw(screen)  # 重力場の描画
        score.update(screen)

        # 画面更新
        pg.display.update()
        tmr += 1
        clock.tick(50)



if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()