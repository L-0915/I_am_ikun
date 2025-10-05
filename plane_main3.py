import random
import pygame
import time
import os
import json
#初始化字体
pygame.init()
pygame.font.init()

from plane_sprites import *

class PlaneGame(object):
    """飞机大战主游戏"""
    def __init__(self):
        print("游戏初始化")
        #1.创建游戏窗口
        self.screen = pygame.display.set_mode(screen_rect.size)
        #2.创建游戏时钟
        self.clock=pygame.time.Clock()

        # 游戏状态和关卡系统
        self.score = 0
        self.current_level = 1
        self.max_unlocked_level = 1  # 最大解锁关卡
        self.level_target_score = 0
        self.level_start_score = 0
        self.game_state = "start"  # start, running, level_complete, level_failed, game_over, level_select
        self.completed_levels = 0

        #4.调用私有方法
        self.__create_sprites()
        self.__load_images()
        self.__create_buttons()

        #5.设置定时器事件-创建敌机 1s
        pygame.time.set_timer(create_enemy_event,1000)
        pygame.time.set_timer(hero_fire_event, 100)
        # 初始道具生成时间（30秒）
        self.last_supply_time = 0  # 上次生成道具的时间
        self.supply_interval = 30000  # 初始道具生成间隔（毫秒）
        self.next_supply_time = 0  # 下一次道具生成的时间
        # 6.加载音效
        self._load_sounds()

        # 7.加载字体
        self.__load_fonts()
        # 8.加载存档
        self.load_game()
        # 初始化第一关
        self.__setup_level(self.current_level)

    def save_game(self):
        """保存游戏进度"""
        save_data = {
            'max_unlocked_level': self.max_unlocked_level,
            'current_level': self.current_level,
            'completed_levels': self.completed_levels,
            'score': self.score
        }
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(save_data, f)
            print("游戏进度已保存")
        except Exception as e:
            print(f"保存游戏失败: {e}")

    def load_game(self):
        """加载游戏进度"""
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, 'r') as f:
                    save_data = json.load(f)
                self.max_unlocked_level = save_data.get('max_unlocked_level', 1)
                self.current_level = save_data.get('current_level', 1)
                self.completed_levels = save_data.get('completed_levels', 0)
                self.score = save_data.get('score', 0)
                print("游戏进度已加载")
            else:
                print("无存档文件，开始新游戏")
        except Exception as e:
            print(f"加载游戏失败: {e}")
    def __setup_level(self, level):
        """设置关卡参数"""
        self.__cleanup_sprites()
        self.current_level = level
        self.level_start_score = self.score
        # 每关目标分数递增：基础1000 + 每关增加1000
        self.level_target_score = self.level_start_score + LEVEL_COMPLETE_SCORE_BASE + (level - 1) * 1000

        # 重新创建精灵组
        self.__create_sprites()
        # 更新英雄子弹伤害
        self.hero.upgrade_bullet_damage(level)
        #更新英雄血量
        self.hero.upgrade_max_health(level)
        # 重置英雄状态（每关开始时恢复生命值）
        self.hero.health = self.hero.max_health

        # 每关减少5%的生成时间，最低不少于10秒
        self.supply_interval = max(5000, int(30000 * (1 - (level - 1) * 0.1)))
        self.next_supply_time = time.time() * 1000 + self.supply_interval
        print(f"开始第 {level} 关，目标分数: {self.level_target_score}")

    def __cleanup_sprites(self):
        """清理精灵组，释放内存"""
        # 清空所有精灵组
        if hasattr(self, 'enemy_group'):
            self.enemy_group.empty()
        if hasattr(self, 'supply_group'):
            self.supply_group.empty()
        if hasattr(self, 'hero') and hasattr(self.hero, 'bullets'):
            self.hero.bullets.empty()

        # 强制垃圾回收
        import gc
        gc.collect()

    def __load_fonts(self):
        """安全地加载字体"""
        self.font = None
        self.small_font = None

        # 尝试多种字体加载方法
        font_methods = [
            # 方法1: 尝试常见的中文字体
            lambda: (pygame.font.SysFont("simhei", 36,bold=True), pygame.font.SysFont("simhei", 24)),
            lambda: (pygame.font.SysFont("microsoftyahei", 36), pygame.font.SysFont("microsoftyahei", 24)),
            lambda: (pygame.font.SysFont("simsun", 36), pygame.font.SysFont("simsun", 24)),
            lambda: (pygame.font.SysFont("kaiti", 36), pygame.font.SysFont("kaiti", 24)),
            # 方法3: 使用默认系统字体
            lambda: (pygame.font.SysFont(None, 36), pygame.font.SysFont(None, 24)),
            # 方法4: 使用英文字体作为备选
            lambda: (pygame.font.SysFont("arial", 36), pygame.font.SysFont("arial", 24)),
        ]

        for method in font_methods:
            try:
                self.font, self.small_font = method()
                # 测试字体是否能正确渲染中文
                test_surface = self.font.render("测试", True, (255, 255, 255))
                if test_surface.get_width() > 0:  # 如果能正常渲染
                    print("字体加载成功")
                    break
                else:
                    print("字体渲染测试失败，继续尝试其他字体")
                    continue
            except Exception as e:
                print(f"字体加载失败: {e}")
                continue

    # 如果所有方法都失败，创建备用字体
        if self.font is None:
            print("使用备用字体")
            self.font = self.BackupFont(36)
            self.small_font = self.BackupFont(24)

    class BackupFont:
        """备用字体类 - 使用图片替代文字"""
        def __init__(self, size):
            self.size = size
            # 创建简单的文字图片缓存
            self.text_cache = {}

        def render(self, text, antialias, color):
            # 检查缓存
            if text in self.text_cache:
                return self.text_cache[text]

            # 创建一个简单的文本表面 - 使用矩形代替文字
            font_size = max(12, min(self.size, 36))
            width = len(text) * font_size
            height = font_size + 10

            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            # 绘制背景矩形
            pygame.draw.rect(surface, color, (0, 0, width, height), border_radius=5)

            # 绘制边框
            pygame.draw.rect(surface, (255, 255, 255), (0, 0, width, height), 2, border_radius=5)

            # 缓存结果
            self.text_cache[text] = surface
            return surface
    def __load_images(self):
        """加载界面图片"""
        try:
            # 开始界面图片
            self.start_image = pygame.image.load("./飞机大战素材/images/start2.png")
            self.start_image = pygame.transform.scale(self.start_image, screen_rect.size)
        except:
            print("开始界面图片加载失败，将使用默认界面")
            self.start_image = None

        try:
            # 暂停界面图片
            self.pause_image = pygame.image.load("./飞机大战素材/images/pause.png")
            self.pause_image = pygame.transform.scale(self.pause_image, screen_rect.size)
        except:
            print("暂停界面图片加载失败，将使用默认界面")
            self.pause_image = None

        try:
            # 游戏结束界面图片
            self.game_over_image = pygame.image.load("./飞机大战素材/images/game_over.png")
            self.game_over_image = pygame.transform.scale(self.game_over_image, screen_rect.size)
        except:
            print("游戏结束界面图片加载失败，将使用默认界面")
            self.game_over_image = None
        #关卡完成和失败图片
        try:
            self.level_complete_image = pygame.image.load("./飞机大战素材/images/level_complete.png")
            self.level_complete_image = pygame.transform.scale(self.level_complete_image, screen_rect.size)
        except:
            print("关卡完成图片加载失败，将使用默认界面")
            self.level_complete_image = None

        try:
            self.level_failed_image = pygame.image.load("./飞机大战素材/images/level_failed.png")
            self.level_failed_image = pygame.transform.scale(self.level_failed_image, screen_rect.size)
        except:
            print("关卡失败图片加载失败，将使用默认界面")
            self.level_failed_image = None

    def __create_buttons(self):
        """创建按钮"""
        # 开始界面按钮
        self.start_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery - 50, 200, 50)
        self.level_select_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 20, 200, 50)
        self.quit_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 90, 200, 50)
        #关卡选择界面
        self.back_to_menu_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.bottom - 80, 200, 50)
        # 暂停界面按钮
        self.resume_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery-20, 200, 50)
        self.menu_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 50, 200, 50)
        # 运行界面按钮
        self.pause_game_button = pygame.Rect(screen_rect.width - 100, 10, 80, 40)
        #关卡完成界面按钮
        self.next_level_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 50, 200, 50)
        self.level_complete_menu_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 120, 200, 50)

        # 关卡失败界面按钮
        self.retry_level_button_text = "我相信你是真ikun，再来一次吧！"
        self.level_failed_menu_button_text = "返回主菜单"
        # 游戏结束界面按钮
        self.restart_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 50, 200, 50)
        self.end_menu_button = pygame.Rect(screen_rect.centerx - 100, screen_rect.centery + 120, 200, 50)

    def __draw_adaptive_button(self, center_x, center_y, text, font=None,
                               color=(100, 100, 255), hover_color=(150, 150, 255),
                               text_color=(255,255,255), min_width=180, min_height=50):
        """
        绘制自适应文字大小的按钮
        返回按钮的Rect对象和文字表面
        """
        if font is None:
            font = self.font

        # 渲染文字表面
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect()

        # 计算按钮大小（文字大小+内边距）
        padding_x = 40  # 水平内边距
        padding_y = 20  # 垂直内边距

        button_width = max(min_width, text_rect.width + padding_x)
        button_height = max(min_height, text_rect.height + padding_y)

        # 创建按钮矩形
        button_rect = pygame.Rect(0, 0, button_width, button_height)
        button_rect.center = (center_x, center_y)

        # 检查鼠标悬停
        mouse_pos = pygame.mouse.get_pos()
        is_hover = button_rect.collidepoint(mouse_pos)

        # 绘制按钮背景
        if is_hover:
            pygame.draw.rect(self.screen, hover_color, button_rect, border_radius=10)
        else:
            pygame.draw.rect(self.screen, color, button_rect, border_radius=10)

        # 绘制按钮边框
        pygame.draw.rect(self.screen, (255, 255, 255), button_rect, 2, border_radius=10)

        # 绘制文字（居中）
        text_rect.center = button_rect.center
        self.screen.blit(text_surf, text_rect)

        return button_rect, is_hover

    def _load_sounds(self):
        """加载音效"""
        try:
            # 背景音乐
            pygame.mixer.music.load("./飞机大战素材/sound/game_music2.ogg")
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)  # 循环播放

            # 音效
            self.shoot_sound = pygame.mixer.Sound("./飞机大战素材/sound/get_bullet2.wav")
            self.explosion_sound = pygame.mixer.Sound("./飞机大战素材/sound/explosion.wav")
            self.get_supply_sound = pygame.mixer.Sound("./飞机大战素材/sound/supply2.wav")
            self.level_complete_sound = pygame.mixer.Sound("./飞机大战素材/sound/level_complete.wav")
            self.level_failed_sound = pygame.mixer.Sound("./飞机大战素材/sound/level_failed.wav")

        except:
            print("音效加载失败，游戏将继续但没有声音")
            self.shoot_sound = None
            self.explosion_sound = None
            self.get_supply_sound = None
    def __create_sprites(self):
        #创建背景精灵和精灵组
        bg1=BackGround()
        bg2=BackGround(True)

        self.back_group=pygame.sprite.Group(bg1,bg2)
        #创建敌机精灵组
        self.enemy_group=pygame.sprite.Group()
        #创建英雄的精灵和精灵组
        self.hero=Hero()
        self.hero_group=pygame.sprite.Group(self.hero)
        # 创建道具精灵组
        self.supply_group = pygame.sprite.Group()

    def start_game(self):
        print("游戏开始")
        while True:
            #1.设置刷新帧率
            self.clock.tick(frame_per_sec)
            #2.事件监听
            self.__event_handler()
            if self.game_state == "running":
                #3.碰撞检测
                self.__check_collide()
                #4.更新/绘制精灵组
                self.__update_sprites()
            elif self.game_state == "start":
                self.__show_start_screen()
            elif self.game_state == "level_select":
                self.__show_level_select_screen()
            elif self.game_state == "paused":
                self.__show_pause_screen()
            elif self.game_state == "level_complete":
                self.__show_level_complete_screen()
            elif self.game_state == "level_failed":
                self.__show_level_failed_screen()
            elif self.game_state == "game_over":
                self.__show_game_over_screen()
            #5.更新显示
            pygame.display.update()

    def __event_handler(self):
        for event in pygame.event.get():
            #判断是否退出游戏
            if event.type==pygame.QUIT:
                self.save_game()  # 退出前保存
                PlaneGame.__game_over()
            # 鼠标点击事件
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                # 开始界面鼠标点击
                if self.game_state == "start":
                    if self.start_button.collidepoint(mouse_pos):
                        self.score = 0
                        self.current_level = 1
                        self.__create_sprites()
                        self.__setup_level(1)
                        self.game_state = "running"
                    elif self.level_select_button.collidepoint(mouse_pos):
                        self.game_state = "level_select"
                    elif self.quit_button.collidepoint(mouse_pos):
                        self.save_game()
                        PlaneGame.__game_over()
                #关卡选择界面
                elif self.game_state == "level_select":
                    # 检查关卡按钮点击
                    level_clicked = self.__check_level_buttons_click(mouse_pos)
                    if level_clicked is not None:
                        self.current_level = level_clicked
                        self.__create_sprites()
                        self.__setup_level(self.current_level)
                        self.game_state = "running"

                    if self.back_to_menu_button.collidepoint(mouse_pos):
                        self.game_state = "start"

                # 游戏运行界面鼠标点击
                elif self.game_state == "running":
                    # 点击暂停按钮
                    if self.pause_game_button.collidepoint(mouse_pos):
                        self.game_state = "paused"
                        # 暂停背景音乐
                        pygame.mixer.music.pause()

                # 暂停界面鼠标点击
                elif self.game_state == "paused":
                    if self.resume_button.collidepoint(mouse_pos):
                        self.game_state = "running"
                        pygame.mixer.music.unpause()
                    elif self.menu_button.collidepoint(mouse_pos):
                        self.game_state = "start"
                #关卡完成界面

                elif self.game_state == "level_complete":
                    if self.next_level_button.collidepoint(mouse_pos):
                        if self.current_level < MAX_LEVEL:
                            self.current_level += 1
                            self.max_unlocked_level = max(self.max_unlocked_level, self.current_level)
                            self.save_game()
                            self.__create_sprites()
                            self.__setup_level(self.current_level)
                            self.game_state = "running"

                            print(f"进入第 {self.current_level} 关")
                        else:
                            self.game_state = "start"
                    elif self.level_complete_menu_button.collidepoint(mouse_pos):
                        self.save_game()
                        self.score = 0
                        self.difficulty = 0
                        self.__create_sprites()  # 重新创建精灵
                        self.game_state = "start"

                # 关卡失败界面
                elif self.game_state == "level_failed":
                    if self.retry_level_button.collidepoint(mouse_pos):
                        current_level = self.current_level
                        self.score = self.level_start_score
                        self.__setup_level(current_level)  # 重新设置关卡
                        self.game_state = "running"
                    elif self.level_failed_menu_button.collidepoint(mouse_pos):
                        self.save_game()
                        self.score = 0
                        self.difficulty = 0
                        self.__create_sprites()  # 重新创建精灵
                        self.game_state = "start"
                # 游戏结束界面鼠标点击
                # elif self.game_state == "game_over":
                #     if self.restart_button.collidepoint(mouse_pos):
                #         self.restart_game()
                #     elif self.end_menu_button.collidepoint(mouse_pos):
                #         # 返回主菜单时重置游戏状态
                #         self.score = 0
                #         self.difficulty = 0
                #         self.__create_sprites()  # 重新创建精灵
                #         self.game_state = "start"

            # 开始界面键盘事件
            elif self.game_state == "start":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:  # 按回车键开始游戏
                        self.score = 0
                        self.current_level = 1
                        self.__create_sprites()
                        self.__setup_level(1)
                        self.game_state = "running"
                    elif event.key == pygame.K_l:
                        self.game_state = "level_select"
                    elif event.key == pygame.K_ESCAPE:  # 按ESC键退出
                        self.save_game()
                        PlaneGame.__game_over()

            # 运行中事件
            elif self.game_state == "running":
                if event.type == create_enemy_event:
                    self.__create_enemy()
                elif event.type == hero_fire_event:
                    self.hero.fire()
                    if self.shoot_sound:
                        self.shoot_sound.play()
                # elif event.type == supply_event:
                #     self.__create_supply()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_b:  # 按B键使用炸弹
                        if self.hero.use_bomb():
                            # 清除所有敌机
                            for enemy in self.enemy_group:
                                enemy.kill()
                                self.score += enemy.score
                            if self.explosion_sound:
                                self.explosion_sound.play()
                    elif event.key == pygame.K_p:  # 按P键暂停游戏
                        self.game_state = "paused"

                        pygame.mixer.music.pause()

            # 暂停界面键盘事件
            elif self.game_state == "paused":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:  # 按P键继续游戏
                        self.game_state = "running"
                    elif event.key == pygame.K_ESCAPE:  # 按ESC键返回开始界面
                        self.save_game()
                        self.game_state = "start"
                        pygame.mixer.music.unpause()

            elif self.game_state == "level_complete":
                if event.type == pygame.KEYDOWN:
                    if (event.key == pygame.K_RETURN) and (self.current_level < MAX_LEVEL):
                        self.current_level += 1
                        self.max_unlocked_level = max(self.max_unlocked_level, self.current_level)
                        self.__create_sprites()
                        self.__setup_level(self.current_level)
                        self.game_state = "running"
                        self.save_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.save_game()
                        self.game_state = "start"

            elif self.game_state == "level_failed":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.score = self.level_start_score
                        self.__create_sprites()
                        self.game_state = "running"
                    elif event.key == pygame.K_ESCAPE:
                        self.save_game()
                        self.game_state = "start"

            # 游戏结束界面键盘事件
            elif self.game_state == "game_over":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # 按R键重新开始
                        self.restart_game()
                    elif event.key == pygame.K_ESCAPE:  # 按ESC键返回开始界面
                        self.game_state = "start"

        # 处理持续按键（仅在游戏运行状态）
        if self.game_state == "running":
            #使用键盘提供的方法获取键盘按键
            key_pressed=pygame.key.get_pressed()
            #判断元组中对应的按键索引
            if key_pressed[pygame.K_RIGHT]:
                self.hero.speed=5
            elif key_pressed[pygame.K_LEFT]:
                self.hero.speed=-5
            elif key_pressed[pygame.K_UP]:
                self.hero.speed=-5
            elif key_pressed[pygame.K_DOWN]:
                self.hero.speed=5
            else:
                self.hero.speed=0

    def __create_enemy(self):
        """根据当前关卡创建敌机"""
        base_count = 1 + min(4, self.current_level // 3)
        enemy_count = random.randint(base_count, base_count + 2)

        for _ in range(enemy_count):
            rand = random.random()
            level_factor = min(1.0, self.current_level / 20.0)

            if rand < 0.7 - level_factor * 0.2:
                enemy_type = "small"
            elif rand < 0.9 - level_factor * 0.1:
                enemy_type = "mid"
            else:
                enemy_type = "big"

            enemy = Enemy(enemy_type, self.current_level)
            self.enemy_group.add(enemy)

    def __create_supply(self):
        """创建道具"""
        supply_type = random.choice(["bomb", "bullet"])
        supply = Supply(supply_type)
        self.supply_group.add(supply)
        # 更新下一次道具生成时间
        self.next_supply_time = time.time() * 1000 + self.supply_interval
    def __check_collide(self):
        # 只在运行状态下检测碰撞
        # if self.game_state != "running":
        #     return
        # 1.子弹与敌机的碰撞
        bullet_enemy_collisions = pygame.sprite.groupcollide(
            self.hero.bullets, self.enemy_group, False, False)

        for bullet, enemies in bullet_enemy_collisions.items():
            for enemy in enemies:
                if enemy.hit():  # 敌机被摧毁
                    self.score += enemy.score
                    enemy.kill()
                    if self.explosion_sound:
                        self.explosion_sound.play()
                bullet.kill()  # 子弹消失

        # 2.英雄与敌机的碰撞
        hero_enemy_collisions = pygame.sprite.spritecollide(
            self.hero, self.enemy_group, True)

        for enemy in hero_enemy_collisions:
            if self.hero.take_damage(enemy.damage):
                # 英雄死亡
                self.hero.kill()
                self.game_state = "level_failed"
                if self.level_failed_sound:
                    self.level_failed_sound.play()
                if self.explosion_sound:
                    self.explosion_sound.play()
        #检测是否应该生成道具
        current_time = time.time() * 1000  # 转换为毫秒
        if current_time >= self.next_supply_time:
            self.__create_supply()
        # 3.英雄与道具的碰撞
        hero_supply_collisions = pygame.sprite.spritecollide(
            self.hero, self.supply_group, True)

        for supply in hero_supply_collisions:
            if supply.supply_type == "bomb":
                self.hero.get_bomb_supply()
            else:  # bullet
                self.hero.activate_double_bullet(18)  # 18秒双倍子弹

            if self.get_supply_sound:
                self.get_supply_sound.play()

        # 4.检查是否完成当前关卡
        if self.score >= self.level_target_score and self.game_state == "running":
            self.save_game()  # 立即保存进度
            self.game_state = "level_complete"
            self.completed_levels += 1
            self.max_unlocked_level = max(self.max_unlocked_level, self.current_level + 1)
            #self.save_game()  # 立即保存进度
            if self.level_complete_sound:
                self.level_complete_sound.play()

    def __update_sprites(self):
        self.back_group.update()
        self.back_group.draw(self.screen)
        self.enemy_group.update(self.current_level)  # 传递当前关卡
        self.enemy_group.draw(self.screen)
        # 绘制敌机血条
        for enemy in self.enemy_group:
            if enemy.enemy_type != "small":  # 小飞机没有血条
                enemy.draw_health_bar(self.screen)
        self.hero_group.update()
        self.hero_group.draw(self.screen)
        # 绘制英雄血条
        self.hero.draw_health_bar(self.screen)
        self.hero.bullets.update()
        self.hero.bullets.draw(self.screen)
        # 更新道具
        self.supply_group.update()
        self.supply_group.draw(self.screen)

        # 绘制UI信息
        self.__draw_ui()

    def __draw_ui(self):
        """绘制游戏UI"""
        # 绘制分数
        score_text = self.font.render(f"分数: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 70))

        # 绘制关卡
        level_text = self.font.render(f"关卡: {self.current_level}/{MAX_LEVEL}", True, (0, 0, 0))
        self.screen.blit(level_text, (10, 30))
        #绘制目标分数
        target_text = self.small_font.render(f"目标: {self.level_target_score}", True, (255, 255, 0))
        self.screen.blit(target_text, (10, 110))

        # 绘制进度条
        progress = min(1.0, (self.score - self.level_start_score) /
                       (self.level_target_score - self.level_start_score))
        bar_width = 200
        bar_height = 20
        bar_x = screen_rect.centerx - bar_width // 2
        bar_y = 10

        pygame.draw.rect(self.screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(self.screen, (0, 255, 0), (bar_x, bar_y, int(bar_width * progress), bar_height))
        pygame.draw.rect(self.screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)
        # 绘制炸弹数量
        bomb_text = self.small_font.render(f"炸弹: {self.hero.bombs}", True, (255, 255, 255))
        self.screen.blit(bomb_text, (screen_rect.width - 90, 60))
        #绘制道具生成时间
        current_time = time.time() * 1000
        remaining_time2 = max(0, (self.next_supply_time - current_time) / 1000)  # 转换为秒

        if remaining_time2 > 0:
            supply_text = self.small_font.render(f"道具: {remaining_time2:.1f}s", True, (180, 0, 255))
            self.screen.blit(supply_text, (screen_rect.width - 150, 120))
        else:
            supply_text = self.small_font.render("道具: 即将生成", True, (180, 0, 255))
            self.screen.blit(supply_text, (screen_rect.width - 150, 120))
        # 绘制双倍子弹状态
        if self.hero.double_bullet:
            remaining_time = max(0, self.hero.double_bullet_end_time - time.time())
            bullet_text = self.small_font.render(f"双倍子弹: {remaining_time:.1f}s", True, (255, 0, 0))
            self.screen.blit(bullet_text, (screen_rect.width - bullet_text.get_width(), 90))

        # 绘制暂停提示
        self.__draw_pause_button()
        # pause_text = self.small_font.render("按P键暂停", True, (255, 255, 255))
        # self.screen.blit(pause_text, (screen_rect.width - 100, screen_rect.height - 30))
    def __draw_pause_button(self):
        """专门绘制暂停按钮，确保在最上层"""
        # 使用醒目的红色和悬停效果
        mouse_pos = pygame.mouse.get_pos()

        # 先绘制一个半透明背景，使按钮在任何背景下都可见
        bg_rect = pygame.Rect(
            self.pause_game_button.x - 5,
            self.pause_game_button.y - 5,
            self.pause_game_button.width + 10,
            self.pause_game_button.height + 10
        )
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))  # 不透明黑色背景
        self.screen.blit(bg_surface, bg_rect)

        if self.pause_game_button.collidepoint(mouse_pos):
            # 悬停状态
            pygame.draw.rect(self.screen, (255, 100, 100), self.pause_game_button, border_radius=8)
        else:
            # 正常状态
            pygame.draw.rect(self.screen, (255, 50, 50), self.pause_game_button, border_radius=8)

        # 添加白色边框
        pygame.draw.rect(self.screen, (255, 255, 255), self.pause_game_button, 2, border_radius=8)

        # 绘制按钮文字
        text_surf = self.font.render("暂停", True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.pause_game_button.center)
        self.screen.blit(text_surf, text_rect)
    def __draw_button(self, button, text, color=(100, 100, 255), hover_color=(150, 150, 255)):
        """绘制按钮"""
        mouse_pos = pygame.mouse.get_pos()

        # 检查鼠标是否在按钮上
        if button.collidepoint(mouse_pos):
            pygame.draw.rect(self.screen, hover_color, button, border_radius=10)
        else:
            pygame.draw.rect(self.screen, color, button, border_radius=10)

        # 绘制按钮边框
        pygame.draw.rect(self.screen, (255, 255, 255), button, 2, border_radius=10)

        # 绘制按钮文字
        text_surf = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=button.center)
        self.screen.blit(text_surf, text_rect)

    def __show_start_screen(self):
        """显示开始界面"""
        if self.start_image:
            # 如果有开始界面图片，显示图片
            self.screen.blit(self.start_image, (0, 0))

            # 绘制标题
            title_font = pygame.font.SysFont("simhei", 72,bold=True)
            title_text = title_font.render("ikun大战", True, (180, 0, 255))
            self.screen.blit(title_text,
                             (screen_rect.centerx - title_text.get_width() // 2,
                              screen_rect.centery - 190))

            # 显示当前进度
            progress_text = self.font.render(f"当前进度: 第{self.max_unlocked_level}关", True, (0, 120, 255))
            self.screen.blit(progress_text,
                             (screen_rect.centerx - progress_text.get_width() // 2,
                              screen_rect.centery - 100))
            # 绘制键盘操作提示
            controls_title = self.font.render("键盘操作:", True, (100, 100, 100))
            self.screen.blit(controls_title,
                             (0,0))

            # 绘制具体控制说明
            controls = [
                "方向键 - 控制飞机移动",
                "Z键 - 自动射击",
                "B键 - 使用炸弹",
                "P键 - 暂停游戏"
            ]

            for i, control in enumerate(controls):
                control_text = self.small_font.render(control, True, (200, 200, 200))
                self.screen.blit(control_text,
                                 (10,
                                    40+i * 30))

            # 绘制游戏说明
            game_info_title = self.font.render("游戏说明:", True, (0, 255, 255))
            self.screen.blit(game_info_title,
                             (screen_rect.width/2 -game_info_title.get_width() // 2,
                              screen_rect.centery + 240))

            # 绘制开始提示
            info=["点击相应按钮开始游戏或选择关卡","也可按回车直接开始游戏"]
            for i, fo in enumerate(info):
                info_text = self.small_font.render(fo, True, (255, 255, 255))
                self.screen.blit(info_text,
                                 (screen_rect.width/2-info_text.get_width() //2,
                                  screen_rect.centery + 280 + i * 30))
            # 在图片上绘制按钮
            self.__draw_button(self.start_button, "开始游戏")
            self.__draw_button(self.level_select_button, "关卡选择")
            self.__draw_button(self.quit_button, "退出游戏")

        else:
            # 如果没有图片，显示默认开始界面
            self.screen.fill((0, 0, 0))
            title_font = pygame.font.SysFont("simhei", 72)
            title_text = title_font.render("飞机大战", True, (255, 255, 0))
            self.screen.blit(title_text,
                            (screen_rect.centerx - title_text.get_width() // 2,
                             screen_rect.centery - 100))
            self.__draw_button(self.start_button, "开始游戏")
            self.__draw_button(self.level_select_button, "关卡选择")
            self.__draw_button(self.quit_button, "退出游戏")

            # 绘制按钮
            self.__draw_button(self.start_button, "开始游戏")
            self.__draw_button(self.quit_button, "退出游戏")

    def __show_level_select_screen(self):
        """显示关卡选择界面"""
        self.screen.fill((0, 0, 0))

        # 标题
        title_text = self.font.render("选择关卡", True, (255, 255, 0))
        self.screen.blit(title_text, (screen_rect.centerx - title_text.get_width() // 2, 50))

        # 显示当前解锁进度
        progress_text = self.small_font.render(f"已解锁: {self.max_unlocked_level}/{MAX_LEVEL} 关", True,
                                               (255, 255, 255))
        self.screen.blit(progress_text, (screen_rect.centerx - progress_text.get_width() // 2, 100))

        # 绘制关卡按钮
        self.__draw_level_buttons()

        # 返回按钮
        self.__draw_button(self.back_to_menu_button, "返回主菜单")

    def __draw_level_buttons(self):
        """绘制关卡选择按钮"""
        button_width = 35
        button_height = 30
        margin = 12
        start_x = 10
        start_y = 150

        for i in range(MAX_LEVEL):
            level = i + 1
            row = i // 10  # 每行10个关卡
            col = i % 10

            button_rect = pygame.Rect(
                start_x + col * (button_width + margin),
                start_y + row * (button_height + margin),
                button_width,
                button_height
            )

            # 判断关卡是否解锁
            if level <= self.max_unlocked_level:
                color = (100, 200, 100)  # 已解锁的绿色
                hover_color = (150, 255, 150)
                text_color = (255, 255, 255)
            else:
                color = (100, 100, 100)  # 未解锁的灰色
                hover_color = (100, 100, 100)
                text_color = (150, 150, 150)

            mouse_pos = pygame.mouse.get_pos()
            if button_rect.collidepoint(mouse_pos) and level <= self.max_unlocked_level:
                pygame.draw.rect(self.screen, hover_color, button_rect, border_radius=8)
            else:
                pygame.draw.rect(self.screen, color, button_rect, border_radius=8)

            pygame.draw.rect(self.screen, (255, 255, 255), button_rect, 2, border_radius=8)

            level_text = self.small_font.render(str(level), True, text_color)
            text_rect = level_text.get_rect(center=button_rect.center)
            self.screen.blit(level_text, text_rect)

            # 存储按钮位置用于点击检测
            if not hasattr(self, 'level_buttons'):
                self.level_buttons = {}
            self.level_buttons[level] = button_rect

    def __check_level_buttons_click(self, mouse_pos):
        """检查关卡按钮点击"""
        if hasattr(self, 'level_buttons'):
            for level, button_rect in self.level_buttons.items():
                if button_rect.collidepoint(mouse_pos) and level <= self.max_unlocked_level:
                    return level
        return None

    def __show_level_complete_screen(self):
        """显示关卡完成界面"""
        self.back_group.draw(self.screen)
        if self.level_complete_image:
            self.screen.blit(self.level_complete_image, (0, 0))
        else:
            # 半透明背景
            overlay = pygame.Surface((screen_rect.width, screen_rect.height))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

        # 恭喜文字
        congrats_text = self.font.render(f"恭喜通过 第 {self.current_level} 关!", True, (255, 165, 0))
        score_text = self.font.render(f"获得分数: {self.score}", True, (0, 255, 0))

        if self.current_level < MAX_LEVEL:
            next_level_text = self.small_font.render(f"已解锁第 {self.current_level + 1} 关", True, (200, 200, 255))
        else:
            next_level_text = self.font.render("太牛了，恭喜通过所有关卡，你就是真ikun!", True, (255, 215, 0))

        self.screen.blit(congrats_text,
                         (screen_rect.centerx - congrats_text.get_width() // 2, screen_rect.centery - 100))
        self.screen.blit(score_text, (screen_rect.centerx - score_text.get_width() // 2, screen_rect.centery - 50))
        self.screen.blit(next_level_text, (screen_rect.centerx - next_level_text.get_width() // 2, screen_rect.centery))

        # 绘制按钮
        if self.current_level < MAX_LEVEL:
            self.__draw_button(self.next_level_button, "下一关")
        else:
            self.__draw_button(self.next_level_button, "返回主菜单")
        self.__draw_button(self.level_complete_menu_button, "返回主菜单")

    def __show_level_failed_screen(self):
        """显示关卡失败界面"""
        if self.level_failed_image:
            self.screen.blit(self.level_failed_image, (0, 0))
        else:
            overlay = pygame.Surface((screen_rect.width, screen_rect.height))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

        failed_text = self.font.render(f"很遗憾，第 {self.current_level} 关 失败！", True, (255, 0, 0))
        score_text = self.font.render(f"获得分数: {self.score}", True, (255, 255, 255))
        target_text = self.small_font.render(f"目标分数: {self.level_target_score}", True, (255, 200, 200))

        self.screen.blit(failed_text, (screen_rect.centerx - failed_text.get_width() // 2, screen_rect.centery - 100))
        self.screen.blit(score_text, (screen_rect.centerx - score_text.get_width() // 2, screen_rect.centery - 50))
        self.screen.blit(target_text, (screen_rect.centerx - target_text.get_width() // 2, screen_rect.centery))

        # 绘制自适应按钮
        button_y_offset = 50
        button_spacing = 70

        # "再来一次"按钮
        retry_button_rect, retry_hover = self.__draw_adaptive_button(
            screen_rect.centerx,
            screen_rect.centery + button_y_offset+30,
            self.retry_level_button_text,
            color=(255, 165, 0),
            hover_color=(150, 200, 255)
        )

        # "返回主菜单"按钮
        menu_button_rect, menu_hover = self.__draw_adaptive_button(
            screen_rect.centerx,
            screen_rect.centery + button_y_offset + button_spacing+30,
            self.level_failed_menu_button_text,
            color=(255,165,0),
            hover_color=(150, 200, 255)
        )

        # 存储按钮矩形用于点击检测
        self.retry_level_button = retry_button_rect
        self.level_failed_menu_button = menu_button_rect

    def __show_pause_screen(self):
        """显示暂停界面"""
        # 绘制当前游戏状态作为背景
        self.back_group.draw(self.screen)
        self.enemy_group.draw(self.screen)
        self.hero_group.draw(self.screen)
        self.hero.bullets.draw(self.screen)
        self.supply_group.draw(self.screen)

        # 半透明覆盖层
        overlay = pygame.Surface((screen_rect.width, screen_rect.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        if self.pause_image:
            # 如果有暂停界面图片，显示图片
            self.screen.blit(self.pause_image, (0, 0))

        # 绘制暂停标题
        pause_text = self.font.render("游戏暂停", True, (255, 255, 0))
        self.screen.blit(pause_text,
                         (screen_rect.centerx - pause_text.get_width() // 2,
                          screen_rect.centery - 100))

        # 绘制按钮
        self.__draw_button(self.resume_button, "继续游戏")
        self.__draw_button(self.menu_button, "返回主菜单")

    def __show_game_over_screen(self):
        """显示游戏结束界面"""
        if self.game_over_image:
            # 如果有游戏结束界面图片，显示图片
            self.screen.blit(self.game_over_image, (0, 0))

            # 在图片上显示分数
            score_text = self.font.render(f"最终分数: {self.score}", True, (255, 255, 255))
            self.screen.blit(score_text,
                             (screen_rect.centerx - score_text.get_width() // 2,
                              screen_rect.centery))

            # 绘制按钮
            self.__draw_button(self.restart_button, "重新开始")
            self.__draw_button(self.end_menu_button, "返回主菜单")
        else:
            # 如果没有图片，显示默认游戏结束界面
            # 半透明背景
            overlay = pygame.Surface((screen_rect.width, screen_rect.height))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

            # 游戏结束文字
            game_over_text = self.font.render("游戏结束", True, (255, 0, 0))
            score_text = self.font.render(f"最终分数: {self.score}", True, (255, 255, 255))

            self.screen.blit(game_over_text,
                             (screen_rect.centerx - game_over_text.get_width() // 2,
                              screen_rect.centery - 50))
            self.screen.blit(score_text,
                             (screen_rect.centerx - score_text.get_width() // 2,
                              screen_rect.centery))

            # 绘制按钮
            self.__draw_button(self.restart_button, "重新开始")
            self.__draw_button(self.end_menu_button, "返回主菜单")

    def restart_game(self):
        """重新开始游戏"""
        # 停止当前音乐
        pygame.mixer.music.stop()
        # 重新初始化游戏
        self.__init__()
        self.game_state = "running"
    @staticmethod
    def __game_over():
        print("游戏结束！")
        pygame.quit()
        exit()
if __name__ == '__main__':
    #创建游戏对象
    game=PlaneGame()
    #启动游戏

    game.start_game()
