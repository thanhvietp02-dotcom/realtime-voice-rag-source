/**
 * Copyright 2025 Beijing Volcano Engine Technology Co., Ltd. All Rights Reserved.
 * SPDX-license-identifier: BSD-3-Clause
 */

import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import Header from '@/components/Header';
import ResizeWrapper from '@/components/ResizeWrapper';
import Menu from './Menu';
import { useIsMobile } from '@/utils/utils';
import Apis from '@/app/index';
import MainArea from './MainArea';
import { ABORT_VISIBILITY_CHANGE, useLeave } from '@/lib/useCommon';
import { RTCConfig, SceneConfig, updateRTCConfig, updateScene, updateSceneConfig } from '@/store/slices/room';
import styles from './index.module.less';

export default function () {

  const leaveRoom = useLeave();       //离开房间，销毁逻辑   constant = 常量
  const dispatch = useDispatch();      //负责修改 Redux 中的全局数据   派发

  const getScenes = async () => {      //// 获取 AI 场景及 RTC 配置，并保存到 Redux  获取场景  Redux 是 React 项目里的“全局数据仓库”。
    const { scenes }: {
      scenes: {
        rtc: RTCConfig;
        scene: SceneConfig;
      }[];
    } = await Apis.Basic.getScenes();   //向后端Python定义的getsence发起一个http post请求获取数据存到前端
    dispatch(updateScene(scenes[0].scene.id));//修改状态
    dispatch(updateSceneConfig(
      scenes.reduce<Record<string, SceneConfig>>((prev, cur) => {
        prev[cur.scene.id] = cur.scene;
        return prev;
      }, {})
    ));
    dispatch(updateRTCConfig(
      scenes.reduce<Record<string, RTCConfig>>((prev, cur) => {
        prev[cur.scene.id] = cur.rtc;
        return prev;
      }, {})
    ));
  }

  useEffect(() => {
    getScenes();    //第一块：加载场景数据
    const isOriginalDemo = window.location.host.startsWith('localhost');  //第二块：监听页面隐藏，并退出通话
    const handler = () => {
      if (
        document.visibilityState === 'hidden' &&
        !sessionStorage.getItem(ABORT_VISIBILITY_CHANGE)
      ) {
        leaveRoom();
      }
    };
    !isOriginalDemo && document.addEventListener('visibilitychange', handler);
    return () => {    //第三块：页面销毁时清除监听
      !isOriginalDemo && document.removeEventListener('visibilitychange', handler);
    };
  }, []);

  return (       // 页面布局：顶部、核心通话区和右侧操作区     MainArea 是前厅与正式通话界面之间的切换开关
    <ResizeWrapper className={styles.container}>
      <Header />
      <div
        className={styles.main}
        style={{
          padding: useIsMobile() ? '' : '24px',
        }}
      >
        <div className={`${styles.mainArea} ${useIsMobile() ? styles.isMobile : ''}`}>
          <MainArea />                
        </div>
        {useIsMobile() ? null : (
          <div className={styles.operationArea}>
            <Menu />
          </div>
        )}
      </div>
    </ResizeWrapper>
  );
}
