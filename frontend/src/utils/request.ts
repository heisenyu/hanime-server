import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { message } from 'ant-design-vue';

//  创建instance实例
const instance: AxiosInstance = axios.create({
    baseURL:'/api',
    // timeout: 10000,
})

//  添加请求拦截
instance.interceptors.request.use(
    // 设置请求头配置信息
    (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig =>{
        //处理指定的请求头

        return config
    },
    // 设置请求错误处理函数
    (error: any): Promise<never> =>{
        message.error('请求发送失败');
        return Promise.reject(error)
    }
)
// 添加响应拦截器
instance.interceptors.response.use(
    // 设置响应正确时的处理函数
    (response: AxiosResponse): AxiosResponse =>{
        // 可以根据业务需求添加成功提示
        if (response.data && response.data.success) {
            message.success(response.data.message || '操作成功');
        }
        return response
    },
    // 设置响应异常时的处理函数
    (error: any): Promise<never> =>{
        if (error.response) {
            switch (error.response.status) {
                case 400:
                    message.error('请求错误');
                    break;
                case 401:
                    message.error('未授权，请重新登录');
                    break;
                case 403:
                    message.error('拒绝访问');
                    break;
                case 404:
                    message.error('请求地址出错');
                    break;
                case 500:
                    message.error('服务器内部错误');
                    break;
                default:
                    message.error(`连接错误 ${error.response.status}`);
            }
        } else {
            message.error('网络连接异常，请稍后再试');
        }
        return Promise.reject(error)
    }
)


// 默认导出
export default instance