import { Clock, User, Sliders, ArrowRight, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Settings: React.FC = () => {
  const navigate = useNavigate();

  const settingsModules = [
    {
      id: 'scheduled-tasks',
      title: '定时任务',
      description: '管理每日任务的执行计划，查看运行历史和手动触发任务',
      icon: <Clock className="w-8 h-8 text-blue-600" />,
      path: '/settings/scheduled-tasks',
      available: true,
      bgColorClass: 'bg-blue-50',
      textColorClass: 'text-blue-600',
      hoverTextColorClass: 'hover:text-blue-700'
    },
    {
      id: 'user-settings',
      title: '用户设置',
      description: '管理用户账户信息、偏好设置和权限配置',
      icon: <User className="w-8 h-8 text-purple-600" />,
      path: '/settings/user',
      available: false,
      bgColorClass: 'bg-purple-50',
      textColorClass: 'text-purple-600',
      hoverTextColorClass: 'hover:text-purple-700'
    },
    {
      id: 'parameter-settings',
      title: '参数设置',
      description: '配置系统参数、策略参数和业务规则',
      icon: <Sliders className="w-8 h-8 text-green-600" />,
      path: '/settings/parameters',
      available: false,
      bgColorClass: 'bg-green-50',
      textColorClass: 'text-green-600',
      hoverTextColorClass: 'hover:text-green-700'
    }
  ];

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">系统设置</h1>
        <p className="text-gray-600 mb-8">管理系统配置和参数设置</p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {settingsModules.map((module) => (
            module.available ? (
              <button
                key={module.id}
                type="button"
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-left transition-all duration-200 hover:shadow-md hover:border-gray-300 cursor-pointer w-full"
                onClick={() => navigate(module.path)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-lg ${module.bgColorClass}`}>
                    {module.icon}
                  </div>
                </div>
                
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {module.title}
                </h3>
                
                <p className="text-sm text-gray-600 mb-4">
                  {module.description}
                </p>
                
                <div className={`flex items-center gap-2 text-sm font-medium ${module.textColorClass} ${module.hoverTextColorClass} transition-colors`}>
                  进入设置
                  <ArrowRight className="w-4 h-4" />
                </div>
              </button>
            ) : (
              <div
                key={module.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 opacity-75 cursor-not-allowed"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-lg ${module.bgColorClass}`}>
                    {module.icon}
                  </div>
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    即将推出
                  </span>
                </div>
                
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {module.title}
                </h3>
                
                <p className="text-sm text-gray-600 mb-4">
                  {module.description}
                </p>
                
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <Lock className="w-4 h-4" />
                  <span>即将推出</span>
                </div>
              </div>
            )
          ))}
        </div>
      </div>
    </div>
  );
};

export default Settings;
