import random
import pygame
import time
import json
import os
#添加屏幕大小的常量
screen_rect=pygame.Rect(0,0,480,700)
#刷新帧率常量
frame_per_sec=60
#创建敌机定时器常量
create_enemy_event=pygame.USEREVENT
#英雄发射子弹
hero_fire_event=pygame.USEREVENT +1
# 道具生成事件
supply_event = pygame.USEREVENT + 2
# 关卡相关常量
MAX_LEVEL = 100
LEVEL_COMPLETE_SCORE_BASE = 1000# 每关基础目标分数
SAVE_FILE = "game_save.json"

class GameSprite(pygame.sprite.Sprite):
    """飞机大战精灵"""
    def __init__(self, image_name, speed=1):
        #调用父类的初始化方法
        super().__init__()
        #定义对象属性
        self.image=pygame.image.load(image_name)
        self.rect=self.image.get_rect()
        self.speed=speed
        pass
    def update(self):
        #在屏幕垂直方向移动
        self.rect.y+=self.speed

class BackGround(GameSprite):
    """游戏背景精灵"""
    def __init__(self, is_alt=False):
        #1.调用父类方法完成精灵的创建
        super().__init__("./飞机大战素材/images/background2.png")
        #2.判断是否是交替图像，如果是，需要设置初始位置
        if is_alt:
            self.rect.y=-self.rect.height

    def update(self):

        #1.调用父类方法实现
        super().update()
        #2.判断是否移出屏幕，如果移出，将图像设置到屏幕上方
        if self.rect.y>=screen_rect.height:
            self.rect.y=-self.rect.height

class Enemy(GameSprite):
    """敌机精灵"""

    def __init__(self, enemy_type="small",level=1):
        self.enemy_type = enemy_type
        self.level = level
        # 根据敌机类型设置不同的属性
        if enemy_type == "small":
            image_path = "./飞机大战素材/images/enemy6.png"

            self.base_speed = random.randint(2, 3)
            #self.speed = base_speed * (1 + (level - 1) * 0.5)  # 每关速度增加50%
            self.health = 1
            self.score = 100 + (level - 1) * 10  # 分数随关卡增加
            self.damage = 20 + (level - 1) * 0.5  # 伤害随关卡增加
        elif enemy_type == "mid":
            image_path = "./飞机大战素材/images/enemy4.png"  # 需要替换为中敌机图片
            self.base_speed = random.randint(1, 3)
            #self.speed = base_speed * (1 + (level - 1) * 0.3)
            self.health = 8 + (level - 1)  # 血量随关卡增加
            self.score = 600 + (level - 1) * 30
            self.damage = 50 + (level - 1) * 1
        else:  # big
            image_path = "./飞机大战素材/images/enemy5.png"  # 需要替换为大敌机图片
            self.base_speed = random.randint(1, 2)
            #self.speed = base_speed * (1 + (level - 1) * 0.1)
            self.health = 20 + (level - 1)
            self.score = 1000 + (level - 1) * 50
            self.damage = 80 + (level - 1)


        #1.调用父类方法，创建敌机精灵，同时指定敌机图片
        super().__init__(image_path)

        #2.指定敌机初始随机速度
        # 初始速度设为基础速度
        self.speed = self.base_speed
        #self.speed=random.randint(2,5)
        #3.指定敌机的初始随机位置
        self.rect.bottom=0
        max_x=screen_rect.width-self.rect.width
        self.rect.x=random.randint(0,max_x)
        # 血条相关
        self.max_health = self.health
        self.health_bar_width = self.rect.width
        self.health_bar_height = 4
    # def update(self):
    #     #1.调用父类方法，保持垂直方向飞行
    #     super().update()
    def update(self, level=1):
        #1.根据关卡调整速度

        level_speed_factor = min(2.0, 1 + (level - 1) * 0.05)
        adjusted_speed = self.speed * level_speed_factor
        self.rect.y += adjusted_speed
         #2.判断是否飞出屏幕，如果是，将敌机从精灵组中删除
        if self.rect.y>=screen_rect.height:
            #print("飞出屏幕，需要删除...")
            #kill方法可以将精灵从所有精灵组中移出，精灵就会被自动销毁
            self.kill()

    def hit(self, damage=1):
        """敌机被击中，返回是否被摧毁"""
        self.health -= damage
        return self.health <= 0

    def draw_health_bar(self, screen):
        """绘制血条"""
        if self.health < self.max_health:
            # 计算血条位置
            bar_x = self.rect.x
            bar_y = self.rect.y - 8
            # 绘制背景条
            pygame.draw.rect(screen, (255, 0, 0),
                             (bar_x, bar_y, self.health_bar_width, self.health_bar_height))
            # 绘制血量条
            health_width = int((self.health / self.max_health) * self.health_bar_width)
            pygame.draw.rect(screen, (0, 255, 0),
                             (bar_x, bar_y, health_width, self.health_bar_height))

    def __del__(self):
        #print("敌机挂了%s"%self.rect)
        pass

class Hero(GameSprite):
    """英雄精灵"""
    def __init__(self):
        #1.调用父类方法，设置图像和速度
        super().__init__("./飞机大战素材/images/me3.png",0)
        #2.设置英雄的初始位置
        self.rect.centerx=screen_rect.centerx
        self.rect.bottom=screen_rect.bottom-120
        #3.创建子弹的精灵组
        self.bullets=pygame.sprite.Group()

        # 4.英雄属性
        self.health = 100
        self.max_health = 100
        # 5.道具相关
        self.bombs = 0
        self.max_bombs = 3
        self.double_bullet = False
        self.double_bullet_end_time = 0
        # 子弹伤害随关卡提升
        self.bullet_damage = 1

    def upgrade_bullet_damage(self, level):
        """根据关卡提升子弹伤害"""
        self.bullet_damage = 1 + (level - 1)   # 每关增加50%伤害

    def upgrade_max_health(self, level):
        self.max_health=100+(level - 1)*50
    def update(self):
        #英雄在水平和垂直方向移动
        key_pressed = pygame.key.get_pressed()
        # 判断元组中对应的按键索引
        if key_pressed[pygame.K_RIGHT] or key_pressed[pygame.K_LEFT]:
            self.rect.x+=self.speed
            #控制英雄不能离开屏幕
            if self.rect.x<0:
                self.rect.x=0
            elif self.rect.right > screen_rect.right:
                self.rect.right=screen_rect.right

        elif key_pressed[pygame.K_UP] or key_pressed[pygame.K_DOWN]:
            self.rect.y+=self.speed
            if self.rect.bottom > screen_rect.bottom-10:
                self.rect.bottom=screen_rect.bottom-10
            elif self.rect.y <0:
                self.rect.y=0
        # 检查双倍子弹效果是否结束
        if self.double_bullet and time.time() > self.double_bullet_end_time:
            self.double_bullet = False

    def fire(self):
        print("发射子弹")
        # for i in (0,1,2):

        #1.创建子弹精灵
        # bullet=Bullet()
        # #2.设置精灵位置
        # bullet.rect.bottom=self.rect.y - 20
        # bullet.rect.centerx=self.rect.centerx

        # 1.创建子弹精灵
        if self.double_bullet:
            # 双倍子弹：发射两发
            bullet1 = Bullet()
            bullet2 = Bullet()
            bullet1.rect.bottom = self.rect.y - 20
            bullet1.rect.centerx = self.rect.centerx - 10
            bullet2.rect.bottom = self.rect.y - 20
            bullet2.rect.centerx = self.rect.centerx + 10
            self.bullets.add(bullet1, bullet2)
        else:
            # 单发子弹
            bullet = Bullet()
            bullet.rect.bottom = self.rect.y - 20
            bullet.rect.centerx = self.rect.centerx
            self.bullets.add(bullet)
        #3.将精灵添加到精灵组
        # self.bullets.add(bullet)

    def use_bomb(self):
        """使用炸弹，返回是否成功使用"""
        if self.bombs > 0:
            self.bombs -= 1
            return True
        return False

    def get_bomb_supply(self):
        """获得炸弹补给"""
        self.bombs = min(self.bombs + 1, self.max_bombs)

    def activate_double_bullet(self, duration=18):
        """激活双倍子弹效果"""
        self.double_bullet = True
        self.double_bullet_end_time = time.time() + duration

    def take_damage(self, damage):
        """受到伤害"""
        self.health = max(0, self.health - damage)
        return self.health <= 0

    def draw_health_bar(self, screen):
        """绘制血条 - 固定在英雄下方"""
        bar_width = 100  # 血条宽度与英雄宽度匹配
        bar_height = 5
        # 计算血条位置 - 在英雄下方
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.y + 120  # 在英雄下方10像素

        # 绘制背景条（红色）
        pygame.draw.rect(screen, (255, 0, 0),
                        (bar_x, bar_y, bar_width, bar_height))
        # 绘制血量条（绿色）
        health_width = int((self.health / self.max_health) * bar_width)
        pygame.draw.rect(screen, (0, 255, 0),
                        (bar_x, bar_y, health_width, bar_height))
        # 绘制边框
        pygame.draw.rect(screen, (255, 255, 255),
                        (bar_x, bar_y, bar_width, bar_height), 1)
class Bullet(GameSprite):
    """子弹精灵"""
    def __init__(self,damage=1):
        #调用父类方法，设置子弹图片和速度
        super().__init__("./飞机大战素材/images/bullet4.png",-6)
        # 子弹射程为屏幕长度的80%
        self.max_distance = screen_rect.height * 1
        self.start_y = 0  # 将在fire方法中设置
        self.damage = damage  # 子弹伤害
    def update(self):
        #调用父类方法，让子弹沿垂直方向飞行
        super().update()
        #判断子弹是否飞出屏幕
        if (self.rect.bottom < 0 or
            (self.start_y - self.rect.y) > self.max_distance):
            self.kill()
    def __del__(self):
        print("子弹被销毁")


class Supply(GameSprite):
    """道具精灵"""

    def __init__(self, supply_type):
        self.supply_type = supply_type  # "bomb" 或 "bullet"

        if supply_type == "bomb":
            image_path = "./飞机大战素材/images/bomb_supply.png"  # 需要替换为炸弹道具图片
        else:
            image_path = "./飞机大战素材/images/bullet_supply2.png"  # 需要替换为子弹道具图片

        super().__init__(image_path, 2)

        # 设置初始位置
        self.rect.bottom = 0
        max_x = screen_rect.width - self.rect.width
        self.rect.x = random.randint(0, max_x)

    def update(self):
        super().update()
        # 判断是否飞出屏幕
        if self.rect.y >= screen_rect.height:
            self.kill()
