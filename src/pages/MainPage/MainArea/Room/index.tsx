/**
 * Copyright 2025 Beijing Volcano Engine Technology Co., Ltd. All Rights Reserved.
 * SPDX-license-identifier: BSD-3-Clause
 */
//用户成功加入 RTC 房间后看到的正式 AI 通话界面。  它本身主要负责组合和展示各个通话功能，不负责创建 RTC 连接。
import { useSelector } from 'react-redux';
import Conversation from './Conversation';
import ToolBar from './ToolBar';
import CameraArea from './CameraArea';
import AudioController from './AudioController';
import { isMobile } from '@/utils/utils';
import style from './index.module.less';
import AiAvatarCard from '@/components/AiAvatarCard';
import { RootState } from '@/store';
import UserTag from '@/components/UserTag';
import FullScreenCard from '@/components/FullScreenCard';
import MobileToolBar from '@/pages/Mobile/MobileToolBar';
import { useScene } from '@/lib/useCommon';

function Room() {
  // 一、读取当前房间状态和 AI 场景配置
  const room = useSelector((state: RootState) => state.room);
  const { isShowSubtitle, scene, isFullScreen } = room;
  const { isAvatarScene } = useScene();
  return (
    <div className={`${style.wrapper} ${isMobile() ? style.mobile : ''}`}>
      {/* 二、手机端的本地画面和操作工具栏 */}
      {isMobile() ? <div className={style.mobilePlayer} id="mobile-local-player" /> : null}
      {isMobile() ? <MobileToolBar /> : null}
      {/* 三、显示当前场景的名称标签 */}
      {isShowSubtitle && !isMobile() ? (
        <UserTag name={scene} className={style.subTitleUserTag} />
      ) : null}
      {/* 四、根据全屏和数字人场景，显示对应的 AI 画面 */}
      {(isFullScreen || isAvatarScene) && !isMobile() ? (
        <FullScreenCard />
      ) : isMobile() && isShowSubtitle ? null : (
        <AiAvatarCard
          showUserTag={!isShowSubtitle}
          showStatus={!isShowSubtitle}
          className={isShowSubtitle ? style.subtitleAiAvatar : ''}
        />
      )}
      {/* 五、显示用户的摄像头或屏幕共享画面 */}
      {isMobile() ? null : <CameraArea />}
      {/* 六、显示用户和 AI 的实时对话字幕 */}
      <Conversation className={style.conversation} showSubtitle={isShowSubtitle} />
      {/* 七、提供麦克风、摄像头、屏幕共享和挂断操作 */}
      <ToolBar className={style.toolBar} />
      {/* 八、显示说话状态，并处理打断 AI */}
      <AudioController className={style.controller} />
      <div className={style.declare}>AI生成内容由大模型生成，不能完全保障真实</div>
    </div>
  );
}

export default Room;
