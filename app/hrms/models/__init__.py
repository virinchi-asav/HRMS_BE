from app.hrms.db import HrmsBase
from app.hrms.models.candidate import CandidateEntity
from app.hrms.models.certificate import CertificateTemplateEntity, TrainingCertificateEntity
from app.hrms.models.client import ClientEntity
from app.hrms.models.current_opening import CurrentOpeningEntity
from app.hrms.models.job import JobEntity
from app.hrms.models.kms_file_view import KmsFileViewEntity
from app.hrms.models.password_reset_token import PasswordResetTokenEntity
from app.hrms.models.profile import ProfileEntity
from app.hrms.models.skill import SkillEntity
from app.hrms.models.skill_configuration import SkillConfigurationEntity
from app.hrms.models.sub_skill import SubSkillEntity
from app.hrms.models.survey import SurveyEntity
from app.hrms.models.task_assessment import (
    BankQuestionEntity,
    BankQuestionOptionEntity,
    QuestionBankEntity,
    TaskAnswerEntity,
    TaskAssigneeEntity,
    TaskEntity,
    TaskQuestionEntity,
    TaskQuestionOptionEntity,
)
from app.hrms.models.testimonial import TestimonialEntity
from app.hrms.models.training import (
    TrainingAssessmentEntity,
    TrainingAssessmentScreenshotEntity,
    TrainingCommentEntity,
    TrainingDayEntryEntity,
    TrainingMaterialEntity,
    TrainingProgramEntity,
    TrainingTraineeEntity,
)
from app.hrms.models.update_request import UpdateRequestEntity
from app.hrms.models.user import UserEntity

__all__ = [
    "HrmsBase",
    "CandidateEntity",
    "CertificateTemplateEntity",
    "ClientEntity",
    "CurrentOpeningEntity",
    "JobEntity",
    "KmsFileViewEntity",
    "PasswordResetTokenEntity",
    "ProfileEntity",
    "SkillEntity",
    "SkillConfigurationEntity",
    "SubSkillEntity",
    "SurveyEntity",
    "BankQuestionEntity",
    "BankQuestionOptionEntity",
    "QuestionBankEntity",
    "TaskAnswerEntity",
    "TaskAssigneeEntity",
    "TaskEntity",
    "TaskQuestionEntity",
    "TaskQuestionOptionEntity",
    "TestimonialEntity",
    "TrainingAssessmentEntity",
    "TrainingAssessmentScreenshotEntity",
    "TrainingCertificateEntity",
    "TrainingCommentEntity",
    "TrainingDayEntryEntity",
    "TrainingMaterialEntity",
    "TrainingProgramEntity",
    "TrainingTraineeEntity",
    "UpdateRequestEntity",
    "UserEntity",
]
