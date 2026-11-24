/**
 * Copyright 2025 Beijing Volcano Engine Technology Co., Ltd. All Rights Reserved.
 * SPDX-license-identifier: BSD-3-Clause
 */
//解析 AI 通过 RTC 发来的二进制消息，并根据消息内容更新 Redux。  handler 直译是“处理器”
import { useDispatch } from 'react-redux';
import logger from './logger';
import {
  setHistoryMsg,
  setInterruptMsg,
  updateAITalkState,
  updateAIThinkState,
} from '@/store/slices/room';
import RtcClient from '@/lib/RtcClient';
import { string2tlv, tlv2String } from '@/utils/utils';

export type AnyRecord = Record<string, any>;

// 一、定义 AI 可能发来的消息类型：状态、字幕和工具调用
export enum MESSAGE_TYPE {
  BRIEF = 'conv',
  SUBTITLE = 'subv',
  FUNCTION_CALL = 'tool',
}

// 二、定义 AI 对话的各种阶段：倾听、思考、说话、被打断和完成
export enum AGENT_BRIEF {
  UNKNOWN,
  LISTENING,
  THINKING,
  SPEAKING,
  INTERRUPTED,
  FINISHED,
}

// 三、定义可以发给 AI 的控制指令
/**
 * @brief 指令类型
 */
export enum COMMAND {
  /**
   * @brief 打断指令
   */
  INTERRUPT = 'interrupt',
  /**
   * @brief 发送外部文本驱动 TTS
   */
  EXTERNAL_TEXT_TO_SPEECH = 'ExternalTextToSpeech',
  /**
   * @brief 发送外部文本驱动 LLM
   */
  EXTERNAL_TEXT_TO_LLM = 'ExternalTextToLLM',
}
/**
 * @brief 打断的类型
 */
export enum INTERRUPT_PRIORITY {
  /**
   * @brief 占位
   */
  NONE,
  /**
   * @brief 高优先级。传入信息直接打断交互，进行处理。
   */
  HIGH,
  /**
   * @brief 中优先级。等待当前交互结束后，进行处理。
   */
  MEDIUM,
  /**
   * @brief 低优先级。如当前正在发生交互，直接丢弃 Message 传入的信息。
   */
  LOW,
}

// 四、将消息类型转换为 RTC 协议中使用的数字编码
export const MessageTypeCode = {
  [MESSAGE_TYPE.SUBTITLE]: 1,
  [MESSAGE_TYPE.FUNCTION_CALL]: 2,
  [MESSAGE_TYPE.BRIEF]: 3,
};

// 五、消息处理中心：解析 AI 消息，并将结果写入 Redux 或回传给 AI
export const useMessageHandler = () => {
  const dispatch = useDispatch();

  const maps = {
    // 处理 AI 状态消息，更新思考、说话、完成和被打断状态
    /**
     * @brief 接收状态变化信息
     * @note https://www.volcengine.com/docs/6348/1415216?s=g
     */
    [MESSAGE_TYPE.BRIEF]: (parsed: AnyRecord) => {
      const { Stage } = parsed || {};
      const { Code, Description } = Stage || {};
      logger.debug('[MESSAGE_TYPE.BRIEF]: ', Code, Description);
      switch (Code) {
        case AGENT_BRIEF.THINKING:
          dispatch(updateAIThinkState({ isAIThinking: true }));
          break;
        case AGENT_BRIEF.SPEAKING:
          dispatch(updateAITalkState({ isAITalking: true }));
          break;
        case AGENT_BRIEF.FINISHED:
          dispatch(updateAITalkState({ isAITalking: false }));
          break;
        case AGENT_BRIEF.INTERRUPTED:
          dispatch(setInterruptMsg());
          break;
        default:
          break;
      }
    },
    // 处理实时字幕消息，将用户和 AI 的文字保存到 Redux
    /**
     * @brief 字幕
     * @note https://www.volcengine.com/docs/6348/1337284?s=g
     */
    // 【字幕链路】云端 ASR 的用户字幕和 LLM 生成的 AI 回复字幕都在此解析
    // 通过 userId 区分说话者，然后将文字写入 Redux 的 msgHistory
    [MESSAGE_TYPE.SUBTITLE]: (parsed: AnyRecord) => {
      const data = parsed.data?.[0] || {};
      /** debounce 记录用户输入文字 */
      if (data) {
        const { text: msg, definite, userId: user, paragraph } = data;
        const isAudioEnable = RtcClient.getAgentEnabled();
        if ((window as any)._debug_mode) {
          logger.debug('handleRoomBinaryMessageReceived', data);
        }
        if (isAudioEnable) {
          dispatch(setHistoryMsg({ text: msg, user, paragraph, definite }));
        }
      }
    },
    // 处理 AI 的工具调用，并将工具执行结果发回给 AI
    /**
     * @brief Function calling
     * @note https://www.volcengine.com/docs/6348/1359441?s=g
     */
    [MESSAGE_TYPE.FUNCTION_CALL]: (parsed: AnyRecord) => {
      const name: string = parsed?.tool_calls?.[0]?.function?.name;
      console.log('[Function Call] - Called by sendUserBinaryMessage');
      const map: Record<string, string> = {
        getcurrentweather: '今天下雪， 最低气温零下10度',
      };

      RtcClient.engine.sendUserBinaryMessage(
        'RobotMan_',
        string2tlv(
          JSON.stringify({
            ToolCallID: parsed?.tool_calls?.[0]?.id,
            Content: map[name.toLocaleLowerCase().replaceAll('_', '')],
          }),
          'func'
        )
      );
    },
  };

  return {
    // 六、统一解析入口：把 RTC 二进制消息转成 JSON，再按消息类型分发处理
    parser: (buffer: ArrayBuffer) => {
      try {
        const { type, value } = tlv2String(buffer);
        maps[type as MESSAGE_TYPE]?.(JSON.parse(value));
        console.log('parser agent回复消息', type, JSON.parse(value));
      } catch (e) {
        logger.debug('parse error', e);
      }
    },
  };
};
